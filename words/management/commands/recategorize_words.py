from django.core.management.base import BaseCommand

from words.models import Word
from words.tasks import parse_word_data, FALLBACK_CATEGORY


class Command(BaseCommand):
    help = "Заново определяет перевод и категорию для слов из категории «Общая» или без категории."

    def handle(self, *args, **options):
        words = Word.objects.filter(category__isnull=True) | Word.objects.filter(
            category__name=FALLBACK_CATEGORY
        )
        words = words.distinct()
        total = words.count()
        self.stdout.write(f"Найдено слов: {total}")
        for i, word in enumerate(words, start=1):
            parse_word_data(word.id)
            self.stdout.write(f"[{i}/{total}] {word.english}")
        self.stdout.write(self.style.SUCCESS("Готово"))