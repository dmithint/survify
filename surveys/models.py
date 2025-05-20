from django.db import models
from django.conf import settings
from django.urls import reverse
import uuid
import secrets
import string

def generate_short_code():
    """Генерирует короткий уникальный код для ссылки"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))

class Survey(models.Model):
    PRIVACY_CHOICES = (
        ('public', 'Публичный'),
        ('link', 'Доступ по ссылке'),
        ('authenticated', 'Только авторизованные пользователи'),
    )
    
    title = models.CharField(verbose_name="Название", max_length=200)
    description = models.TextField(verbose_name="Описание", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Создатель", on_delete=models.CASCADE, related_name='created_surveys')
    created_at = models.DateTimeField(verbose_name="Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Дата обновления", auto_now=True)
    privacy = models.CharField(verbose_name="Приватность", max_length=20, choices=PRIVACY_CHOICES, default='link')
    short_code = models.CharField(verbose_name="Короткий код", max_length=8, unique=True, default=generate_short_code)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('survey_detail', args=[str(self.id)])

class Question(models.Model):
    TYPE_CHOICES = (
        ('text', 'Текстовый ответ'),
        ('radio', 'Один вариант'),
        ('checkbox', 'Несколько вариантов'),
    )
    
    survey = models.ForeignKey(Survey, verbose_name="Опрос", on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(verbose_name="Текст вопроса", max_length=500)
    question_type = models.CharField(verbose_name="Тип вопроса", max_length=20, choices=TYPE_CHOICES)
    required = models.BooleanField(verbose_name="Обязательный", default=False)
    order = models.IntegerField(verbose_name="Порядок", default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class Choice(models.Model):
    question = models.ForeignKey(Question, verbose_name="Вопрос", on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(verbose_name="Текст варианта", max_length=200)
    order = models.IntegerField(verbose_name="Порядок", default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='answers')
    anonymous_user = models.UUIDField(default=uuid.uuid4, null=True, blank=True)
    text_answer = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Answer to {self.question.text}"

class AnswerChoice(models.Model):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='selected_choices')
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='selected_in')
    
    def __str__(self):
        return f"{self.choice.text}"

class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='survey_responses')
    anonymous_user = models.UUIDField(default=uuid.uuid4, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.user:
            return f"{self.user}'s response to {self.survey.title}"
        return f"Anonymous response to {self.survey.title}"
