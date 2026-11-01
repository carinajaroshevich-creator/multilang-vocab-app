"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.urls import path
from django.contrib.auth import views as auth_views # Импортируем встроенные представления
from words import views as words_views

urlpatterns = [
    path('register/', words_views.register, name='register'),

    # Вход и Выход (используем готовые от Django)
    path('login/', auth_views.LoginView.as_view(template_name='words/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('admin/', admin.site.urls),
    path('', include('words.urls')), # Подключаем ссылки нашего приложения к главному адресу сайта
]