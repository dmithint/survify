from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('survey/create/', views.survey_create, name='survey_create'),
    path('survey/<int:pk>/', views.survey_detail, name='survey_detail'),
    path('survey/<int:pk>/edit/', views.survey_edit, name='survey_edit'),
    path('survey/<int:pk>/delete/', views.survey_delete, name='survey_delete'),
    path('survey/<int:pk>/take/', views.survey_take, name='survey_take'),
    path('survey/<int:pk>/results/', views.survey_results, name='survey_results'),
    path('survey/<int:survey_id>/question/add/', views.question_create, name='question_create'),
    path('question/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('s/<str:short_code>/', views.survey_by_link, name='survey_by_link'),
] 