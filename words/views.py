from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
import datetime

from .models import Category, Word, UserExample
from .forms import UserRegisterForm
from .tasks import parse_word_data, ensure_default_categories, FALLBACK_CATEGORY, PENDING_TEXT

# Сколько новых слов один пользователь может добавить за 24 часа
DAILY_NEW_WORDS_LIMIT = getattr(settings, "DAILY_NEW_WORDS_LIMIT", 50)


def words_added_last_24h(user):
    since = timezone.now() - datetime.timedelta(hours=24)
    return Word.objects.filter(user=user, created_at__gte=since).count()


@login_required
def vocabulary_home(request):
    """Главная страница словаря с разделением категорий по языкам."""
    current_lang = request.GET.get('lang', 'en')

    if request.method == 'POST':
        english_word = request.POST.get('english_word', '').strip()
        selected_lang = request.POST.get('language', current_lang)

        if english_word:
            already_exists = Word.objects.filter(
                english=english_word,
                user=request.user,
                language=selected_lang
            ).exists()

            # Дневной лимит на новые слова (для администратора не действует)
            if (not already_exists
                    and not request.user.is_superuser
                    and words_added_last_24h(request.user) >= DAILY_NEW_WORDS_LIMIT):
                messages.warning(
                    request,
                    f"Достигнут лимит: не более {DAILY_NEW_WORDS_LIMIT} новых слов за 24 часа. "
                    "Попробуйте добавить слово позже."
                )
                return redirect(f"/?lang={selected_lang}")

            ensure_default_categories(selected_lang)
            default_category = Category.objects.get(
                name=FALLBACK_CATEGORY,
                language=selected_lang
            )

            word_obj, created = Word.objects.get_or_create(
                english=english_word,
                user=request.user,
                language=selected_lang,
                defaults={
                    'translation': "Ожидает перевода...",
                    'category': default_category
                }
            )

            # Переводим новое слово, а также повторяем попытку для тех,
            # что раньше не перевелись (например, из-за ошибки API)
            if created or word_obj.translation == PENDING_TEXT:
                # Сначала берётся готовый перевод из базы, и только потом запрос к Gemini
                parse_word_data(word_obj.id)
                word_obj.refresh_from_db()
                if word_obj.translation == PENDING_TEXT:
                    messages.error(
                        request,
                        f"Не удалось получить перевод слова «{word_obj.english}»: сервис перевода "
                        "сейчас недоступен или достигнут его лимит. Добавьте слово ещё раз чуть позже."
                    )

            return redirect(f"/?lang={selected_lang}")

    # Показываем только категории, в которых есть слова текущего пользователя
    categories = Category.objects.filter(
        language=current_lang,
        word__user=request.user
    ).distinct().order_by('name')
    user_words = Word.objects.filter(user=request.user, language=current_lang).order_by('-created_at')

    context = {
        'categories': categories,
        'words': user_words,
        'total_words': user_words.count(),
        'current_lang': current_lang,
        'languages': Word.LANGUAGES,
    }

    return render(request, 'words/index.html', context)


@login_required
def word_training(request):
    """Интервальная тренировка слов с учетом текущего языка."""
    current_lang = request.GET.get('lang', 'en')
    word_id = request.GET.get('word_id')
    show_answer = request.GET.get('show_answer') == '1'
    action = request.GET.get('action')

    if word_id and action:
        word_item = get_object_or_404(Word, id=word_id, user=request.user)
        lang_to_redirect = word_item.language
        if action == 'correct':
            word_item.next_review = timezone.now() + datetime.timedelta(days=1)
        elif action == 'wrong':
            word_item.next_review = timezone.now()
        word_item.save()

        return redirect(f"{reverse('word_training')}?lang={lang_to_redirect}")

    word = None
    if word_id:
        word = get_object_or_404(Word, id=word_id, user=request.user)
        if word.language != current_lang:
            word = None

    if not word:
        word = Word.objects.filter(
            user=request.user,
            language=current_lang,
            next_review__lte=timezone.now()
        ).order_by('?').first()

        if not word:
            word = Word.objects.filter(
                user=request.user,
                language=current_lang
            ).order_by('?').first()

    words_to_review_count = Word.objects.filter(
        user=request.user,
        language=current_lang,
        next_review__lte=timezone.now()
    ).count()

    context = {
        'word': word,
        'show_answer': show_answer,
        'words_to_review_count': words_to_review_count,
        'current_lang': current_lang,
    }
    return render(request, 'words/training.html', context)


def register(request):
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('vocab_home')
    else:
        form = UserRegisterForm()
    return render(request, 'words/register.html', {'form': form})


@login_required
def add_user_example(request, word_id):
    """Добавление пользовательского примера к слову."""
    word = get_object_or_404(Word, id=word_id, user=request.user)
    if request.method == 'POST':
        example_text = request.POST.get('user_example_text', '').strip()
        if example_text:
            UserExample.objects.create(word=word, text=example_text)

    return redirect(f"/?lang={word.language}")


@login_required
def delete_word(request, word_id):
    """Безопасное удаление слова."""
    word = get_object_or_404(Word, id=word_id, user=request.user)
    lang = word.language

    if request.method == 'POST':
        word.delete()

    return redirect(f"/?lang={lang}")