from rest_framework import serializers
from .models import Survey, Question, Choice, Answer, AnswerChoice, SurveyResponse
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'email']

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'required', 'order', 'choices']

class SurveySerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    questions_count = serializers.SerializerMethodField()
    responses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Survey
        fields = ['id', 'title', 'description', 'created_by', 'created_at', 
                  'updated_at', 'privacy', 'short_code', 'questions_count', 
                  'responses_count']
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'short_code']
    
    def get_questions_count(self, obj):
        return obj.questions.count()
    
    def get_responses_count(self, obj):
        return obj.responses.count()

class SurveyDetailSerializer(SurveySerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta(SurveySerializer.Meta):
        fields = SurveySerializer.Meta.fields + ['questions']

class AnswerChoiceSerializer(serializers.ModelSerializer):
    choice_text = serializers.CharField(source='choice.text', read_only=True)
    
    class Meta:
        model = AnswerChoice
        fields = ['id', 'choice', 'choice_text']

class AnswerSerializer(serializers.ModelSerializer):
    selected_choices = AnswerChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'question', 'text_answer', 'selected_choices', 'created_at']
        read_only_fields = ['created_at']

class SurveyResponseSerializer(serializers.ModelSerializer):
    answers = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = SurveyResponse
        fields = ['id', 'survey', 'user', 'submitted_at', 'answers']
        read_only_fields = ['submitted_at']
    
    def get_answers(self, obj):
        # Получаем все ответы для данного пользователя (или анонимного пользователя) и опроса
        user_filter = {'user': obj.user} if obj.user else {'anonymous_user': obj.anonymous_user}
        answers = Answer.objects.filter(survey=obj.survey, **user_filter)
        return AnswerSerializer(answers, many=True).data

class TextAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    text_answer = serializers.CharField(allow_blank=True)

class ChoiceAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )

class SurveySubmitSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    text_answers = TextAnswerSubmitSerializer(many=True, required=False)
    choice_answers = ChoiceAnswerSubmitSerializer(many=True, required=False) 