import os
from celery import shared_task
from django.conf import settings
from google import genai
from google.genai import types
from .models import Word


@shared_task
def parse_word_data(word_id):
    """Фоновая задача для автоматического заполнения перевода, транскрипции, рода и примера через Gemini API."""
    try:
        word_obj = Word.objects.get(id=word_id)
    except Word.DoesNotExist:
        return

    # Инициализируем клиент Gemini, явно передавая ключ из настроек Django
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Формируем точный промпт в зависимости от языка слова
    lang_name = word_obj.get_language_display()

    prompt = f"""
    Ты — лингвистический помощник. Проанализируй слово "{word_obj.english}" на языке: {lang_name}.
    Верни ответ строго в следующем формате (без лишнего текста, только эти 4 строки):

    Перевод: [красивый перевод на русский язык]
    Транскрипция: [произношение русскими буквами кириллицей, с ударением заглавной буквой, например: [эйсинхрОнас] или [боскИто]]
    Род: [для немецкого/итальянского укажи: m (если мужской/der/il), f (если женский/die/la), n (если средний/das), или none если нет рода или язык английский]
    Пример: [краткое примерное предложение на целевом языке с переводом на русский]
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text_result = response.text.strip()

        # Парсим ответ от модели построчно
        lines = text_result.split('\n')
        translation = ""
        transcription = ""
        gender = "none"
        example = ""

        for line in lines:
            if line.startswith("Перевод:"):
                translation = line.replace("Перевод:", "").strip()
            elif line.startswith("Транскрипция:"):
                transcription = line.replace("Транскрипция:", "").strip()
            elif line.startswith("Род:"):
                raw_gender = line.replace("Род:", "").strip().lower()
                if raw_gender in ['m', 'f', 'n']:
                    gender = raw_gender
            elif line.startswith("Пример:"):
                example = line.replace("Пример:", "").strip()

        # Сохраняем данные в объект слова
        if translation and translation != "Ожидает перевода...":
            word_obj.translation = translation
        if transcription:
            word_obj.transcription = transcription
        word_obj.gender = gender
        if example:
            word_obj.example_sentence = example

        word_obj.save()

    except Exception as e:
        print(f"Ошибка при запросе к Gemini API: {e}")