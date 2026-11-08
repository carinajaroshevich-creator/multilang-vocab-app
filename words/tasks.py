import logging

from celery import shared_task
from django.conf import settings
from google import genai

from .models import Word, Category

logger = logging.getLogger(__name__)

FALLBACK_CATEGORY = "Общая"

# Категории, которые создаются автоматически для каждого языка.
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


@shared_task
def parse_word_data(word_id):
    """Заполняет перевод, транскрипцию, род, пример и категорию слова через Gemini API."""
    try:
        word_obj = Word.objects.get(id=word_id)
    except Word.DoesNotExist:
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
                transcription = line.replace("Транскрипция:", "", 1).strip().strip("[]() ")
            elif line.startswith("Род:"):
                raw_gender = line.replace("Род:", "", 1).strip().lower()
                if raw_gender in ("m", "f", "n"):
                    gender = raw_gender
            elif line.startswith("Пример:"):
                example = line.replace("Пример:", "", 1).strip()
            elif line.startswith("Категория:"):
                category_name = line.replace("Категория:", "", 1).strip().strip("[]. ")

        if translation and translation != "Ожидает перевода...":
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