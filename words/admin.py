from django.contrib import admin
from .models import Category, Word, UserExample


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    # Добавляем 'user' и 'next_review' в список, чтобы видеть владельца слова и дату тренировки
    list_display = ('english', 'translation', 'category', 'user', 'next_review', 'created_at')
    # Добавляем фильтрацию по пользователям, чтобы можно было отсекать слова конкретного друга
    list_filter = ('category', 'user')
    search_fields = ('english', 'translation')


@admin.register(UserExample)
class UserExampleAdmin(admin.ModelAdmin):
    # Настраиваем отображение для пользовательских предложений
    list_display = ('word', 'get_user', 'text', 'created_at')
    search_fields = ('text', 'word__english')

    # Небольшая магия Django, чтобы прямо в списке предложений видеть, какой юзер его написал
    def get_user(self, obj):
        return obj.word.user
    get_user.short_description = 'Пользователь'

