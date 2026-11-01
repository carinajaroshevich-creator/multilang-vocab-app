import os
import re
from django.core.management.base import BaseCommand
from words.models import Category, Word


class Command(BaseCommand):
    help = 'Импортирует 500 базовых слов из текстового файла в базу данных'

    def handle(self, *args, **options):
        file_path = '500_essential_english_words.txt'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Файл {file_path} не найден в корневой директории!'))
            return

        self.stdout.write('Начало импорта слов...')

        current_category = None
        words_created = 0
        categories_created = 0

        # Регулярное выражение для разбора строчки со словом:
        # Пример строки: "002. bug                       [баг]                — ошибка в программе, жук"
        word_regex = re.compile(r'^\d+\.\s+([a-zA-Z\s\(\)\-\/,\']+?)\s+(\[.+?\])\s+—\s+(.+)$')

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()

                # 1. Ищем категорию
                if line.startswith('📌 КАТЕГОРИЯ:'):
                    category_name = line.replace('📌 КАТЕГОРИЯ:', '').strip().title()
                    current_category, created = Category.objects.get_or_create(name=category_name)
                    if created:
                        categories_created += 1
                    continue

                # 2. Если категория уже определена, пробуем распарсить слово
                if current_category:
                    match = word_regex.match(line)
                    if match:
                        eng_word = match.group(1).strip()
                        transcription = match.group(2).strip()
                        translation = match.group(3).strip()

                        # Добавляем или обновляем слово в базе
                        word, created = Word.objects.get_or_create(
                            english=eng_word,
                            defaults={
                                'translation': translation,
                                'transcription': transcription,
                                'category': current_category
                            }
                        )
                        if created:
                            words_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Импорт успешно завершен! Создано категорий: {categories_created}, импортировано слов: {words_created}'
        ))