from django.urls import path
from . import views

urlpatterns = [
    path('', views.vocabulary_home, name='vocab_home'),
    path('training/', views.word_training, name='word_training'),
    path('word/<int:word_id>/add-example/', views.add_user_example, name='add_user_example'),
    path('word/<int:word_id>/delete/', views.delete_word, name='delete_word'),
]