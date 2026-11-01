from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    LANGUAGES = [
        ('en', 'Английский'),
        ('de', 'Немецкий'),
        ('it', 'Итальянский'),
    ]

    name = models.CharField(max_length=100, verbose_name="Название категории")
    language = models.CharField(
        max_length=2,
        choices=LANGUAGES,
        default='en',
        verbose_name="Язык"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return f"{self.name} ({self.get_language_display()})"


class Word(models.Model):
    LANGUAGES = [
        ('en', 'Английский'),
        ('de', 'Немецкий'),
        ('it', 'Итальянский'),
    ]

    GENDER_CHOICES = [
        ('none', '—'),
        ('m', 'Мужской (der/il)'),
        ('f', 'Женский (die/la)'),
        ('n', 'Средний (das)'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='words',
        verbose_name="Пользователь"
    )
    english = models.CharField(max_length=255, verbose_name="Слово")
    language = models.CharField(
        max_length=2,
        choices=LANGUAGES,
        default='en',
        verbose_name="Язык"
    )
    gender = models.CharField(
        max_length=4,
        choices=GENDER_CHOICES,
        default='none',
        verbose_name="Род"
    )

    translation = models.CharField(
        max_length=255,
        default="Ожидает перевода...",
        blank=True,
        null=True,
        verbose_name="Перевод"
    )
    transcription = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Транскрипция"
    )
    example_sentence = models.TextField(
        blank=True,
        null=True,
        verbose_name="Пример предложения"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категория"
    )
    next_review = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата следующего повторения"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Слово"
        verbose_name_plural = "Слова"

    def __str__(self):
        return f"{self.english} ({self.get_language_display()}) -> {self.translation}"


class UserExample(models.Model):
    word = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name='user_examples',
        verbose_name="Слово"
    )
    text = models.TextField(verbose_name="Ваше предложение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Пример пользователя"
        verbose_name_plural = "Примеры пользователей"

    def __str__(self):
        return f"Пример для {self.word.english}: {self.text[:30]}..."