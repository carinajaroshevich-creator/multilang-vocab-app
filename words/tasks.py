import logging
import re

from celery import shared_task
from django.conf import settings
from google import genai

from .models import Word, Category

logger = logging.getLogger(__name__)

FALLBACK_CATEGORY = "Общая"
PENDING_TEXT = "Ожидает перевода..."

# Набор категорий, которые создаются автоматически для каждого языка.
# Gemini выбирает одну из них для нового слова.
DEFAULT_CATEGORIES = [
    "Программирование и ИТ",
    "Местоимения и вопросы",
    "Основные глаголы",
    "Офис и время",
    "Разговорные фразы",
    "Прилагательные",
    "Повседневная жизнь",
    "Еда и напитки",
    "Люди и семья",
    "Природа и животные",
    "Здоровье и тело",
    "Путешествия",
    "Предлоги и союзы",
    "Числительные и количество",
    FALLBACK_CATEGORY,
]


def ensure_default_categories(language):
    """Создаёт стандартные категории для языка, если их ещё нет."""
    for name in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(name=name, language=language)


def _clean(value):
    """Убирает markdown-звёздочки и лишние пробелы из ответа модели."""
    return value.replace("*", "").strip()


def _copy_from_existing(word_obj):
    """Кэш переводов: если такое слово уже переводилось (у любого пользователя),
    копируем готовые данные и не тратим запрос к Gemini.
    Берём только слова с настоящей категорией (не «Общая»), чтобы
    повторная расстановка категорий через Gemini продолжала работать."""
    donor = (
        Word.objects
        .filter(language=word_obj.language, english__iexact=word_obj.english)
        .exclude(id=word_obj.id)
        .exclude(translation__isnull=True)
        .exclude(translation="")
        .exclude(translation=PENDING_TEXT)
        .exclude(category__isnull=True)
        .exclude(category__name=FALLBACK_CATEGORY)
        .order_by("id")
        .first()
    )
    if donor is None:
        return False

    word_obj.translation = donor.translation
    word_obj.transcription = donor.transcription
    word_obj.gender = donor.gender
    word_obj.example_sentence = donor.example_sentence
    word_obj.category = donor.category
    word_obj.save()
    return True


@shared_task
def parse_word_data(word_id):
    """Заполняет перевод, транскрипцию, род, пример и категорию слова через Gemini API."""
    try:
        word_obj = Word.objects.get(id=word_id)
    except Word.DoesNotExist:
        return

    # Сначала пробуем взять готовый перевод из базы (экономит запросы к Gemini)
    if _copy_from_existing(word_obj):
        return

    ensure_default_categories(word_obj.language)
    category_names = list(
        Category.objects.filter(language=word_obj.language).values_list("name", flat=True)
    )
    categories_str = ", ".join(category_names)

    lang_name = word_obj.get_language_display()

    prompt = f"""
    Ты — лингвистический помощник. Проанализируй слово "{word_obj.english}" на языке: {lang_name}.
    Верни ответ строго в следующем формате (без лишнего текста, только эти 5 строк):

    Перевод: [красивый перевод на русский язык]
    Транскрипция: [произношение русскими буквами кириллицей, с ударением заглавной буквой, например: эйсинхрОнас или боскИто, БЕЗ квадратных скобок]
    Род: [для немецкого/итальянского укажи: m (если мужской/der/il), f (если женский/die/la), n (если средний/das), или none если нет рода или язык английский]
    Пример: [краткое примерное предложение на целевом языке с переводом на русский]
    Категория: [выбери ОДНО название строго из списка: {categories_str}. Если ничего не подходит, напиши: {FALLBACK_CATEGORY}]
    """

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text_result = response.text.strip()

        translation = ""
        transcription = ""
        gender = "none"
        example = ""
        category_name = ""

        for raw_line in text_result.split("\n"):
            line = _clean(raw_line)
            if line.startswith("Перевод:"):
                translation = line.replace("Перевод:", "", 1).strip()
            elif line.startswith("Транскрипция:"):
                # убираем скобки, т.к. шаблон сам добавляет [ ]
                transcription = line.replace("Транскрипция:", "", 1).strip().strip("[]() ")
            elif line.startswith("Род:"):
                raw_gender = line.replace("Род:", "", 1).strip().lower()
                if raw_gender in ("m", "f", "n"):
                    gender = raw_gender
            elif line.startswith("Пример:"):
                example = line.replace("Пример:", "", 1).strip()
            elif line.startswith("Категория:"):
                category_name = line.replace("Категория:", "", 1).strip().strip("[]. ")

        if translation and translation != PENDING_TEXT:
            word_obj.translation = translation
        if transcription:
            word_obj.transcription = transcription
        word_obj.gender = gender
        if example:
            word_obj.example_sentence = example

        # Подбираем категорию из существующих (без учёта регистра)
        category = None
        if category_name:
            category = Category.objects.filter(
                language=word_obj.language, name__iexact=category_name
            ).first()
        if category is None and word_obj.category is None:
            category = Category.objects.filter(
                language=word_obj.language, name=FALLBACK_CATEGORY
            ).first()
        if category is not None:
            word_obj.category = category

        word_obj.save()

    except Exception:
        logger.exception("Ошибка при запросе к Gemini API (слово id=%s)", word_id)