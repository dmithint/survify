from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .models import Survey, Question, Choice, Answer, AnswerChoice, SurveyResponse
from .serializers import (
    SurveySerializer, SurveyDetailSerializer, QuestionSerializer,
    ChoiceSerializer, AnswerSerializer, SurveyResponseSerializer,
    SurveySubmitSerializer
)

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение, которое позволяет владельцам объекта редактировать его.
    """
    def has_object_permission(self, request, view, obj):
        # Разрешения на чтение разрешены для любого запроса
        if request.method in permissions.SAFE_METHODS:
            return True
        # Разрешения на запись только для владельца
        return obj.created_by == request.user

class SurveyViewSet(viewsets.ModelViewSet):
    """
    API для работы с опросами.
    """
    serializer_class = SurveySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        # Если пользователь суперпользователь, показываем все опросы
        if user.is_superuser:
            return Survey.objects.all()
        
        # Для обычных пользователей показываем их опросы и публичные опросы
        return Survey.objects.filter(
            created_by=user
        ) | Survey.objects.filter(
            privacy='public'
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SurveyDetailSerializer
        return SurveySerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        description='Получить опрос по короткому коду',
        parameters=[
            OpenApiParameter(name='code', description='Короткий код опроса', required=True, type=str)
        ],
        responses={200: SurveyDetailSerializer}
    )
    @action(detail=False, methods=['get'], url_path='by-code/(?P<code>[^/.]+)', 
            permission_classes=[permissions.AllowAny])
    def by_code(self, request, code=None):
        """Получение опроса по короткому коду."""
        survey = get_object_or_404(Survey, short_code=code)
        
        # Проверяем доступность опроса
        if survey.privacy == 'authenticated' and not request.user.is_authenticated:
            return Response(
                {"detail": "Для просмотра этого опроса необходимо авторизоваться."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SurveyDetailSerializer(survey)
        return Response(serializer.data)

class QuestionViewSet(viewsets.ModelViewSet):
    """
    API для работы с вопросами опроса.
    """
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(survey__created_by=self.request.user)

    def perform_create(self, serializer):
        survey_id = self.request.data.get('survey')
        survey = get_object_or_404(Survey, pk=survey_id)
        
        # Проверяем, что пользователь является создателем опроса
        if survey.created_by != self.request.user:
            self.permission_denied(self.request)
        
        # Устанавливаем порядок нового вопроса
        order = survey.questions.count() + 1
        serializer.save(survey=survey, order=order)

class SurveyResponseAPIView(generics.CreateAPIView):
    """
    API для отправки ответа на опрос.
    """
    serializer_class = SurveySubmitSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description='Отправить ответы на опрос',
        request=SurveySubmitSerializer,
        responses={201: SurveyResponseSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        survey_id = serializer.validated_data['survey_id']
        survey = get_object_or_404(Survey, pk=survey_id)
        
        # Проверяем доступность опроса
        if survey.privacy == 'authenticated' and not request.user.is_authenticated:
            return Response(
                {"detail": "Для прохождения этого опроса необходимо авторизоваться."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Если пользователь аутентифицирован, проверяем, не проходил ли он уже этот опрос
        if request.user.is_authenticated:
            already_responded = SurveyResponse.objects.filter(
                survey=survey,
                user=request.user
            ).exists()
            
            if already_responded:
                return Response(
                    {"detail": "Вы уже проходили этот опрос."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        with transaction.atomic():
            # Создаем запись об ответе на опрос
            survey_response = SurveyResponse.objects.create(
                survey=survey,
                user=request.user if request.user.is_authenticated else None
            )
            
            # Обрабатываем текстовые ответы
            for text_answer_data in serializer.validated_data.get('text_answers', []):
                question = get_object_or_404(Question, pk=text_answer_data['question_id'])
                
                # Проверяем, что вопрос принадлежит опросу
                if question.survey.id != survey.id:
                    continue
                
                # Создаем ответ
                Answer.objects.create(
                    question=question,
                    survey=survey,
                    user=request.user if request.user.is_authenticated else None,
                    anonymous_user=None if request.user.is_authenticated else survey_response.anonymous_user,
                    text_answer=text_answer_data['text_answer']
                )
            
            # Обрабатываем ответы с выбором вариантов
            for choice_answer_data in serializer.validated_data.get('choice_answers', []):
                question = get_object_or_404(Question, pk=choice_answer_data['question_id'])
                
                # Проверяем, что вопрос принадлежит опросу
                if question.survey.id != survey.id:
                    continue
                
                # Создаем ответ
                answer = Answer.objects.create(
                    question=question,
                    survey=survey,
                    user=request.user if request.user.is_authenticated else None,
                    anonymous_user=None if request.user.is_authenticated else survey_response.anonymous_user
                )
                
                # Добавляем выбранные варианты
                for choice_id in choice_answer_data['choice_ids']:
                    choice = get_object_or_404(Choice, pk=choice_id)
                    
                    # Проверяем, что вариант принадлежит вопросу
                    if choice.question.id != question.id:
                        continue
                    
                    AnswerChoice.objects.create(
                        answer=answer,
                        choice=choice
                    )
        
        response_serializer = SurveyResponseSerializer(survey_response)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class UserSurveyResponsesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для получения ответов пользователя на опросы.
    """
    serializer_class = SurveyResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SurveyResponse.objects.filter(user=self.request.user)

class SurveyResultsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для получения результатов опроса (только для владельца опроса).
    """
    serializer_class = SurveyResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        survey_id = self.kwargs.get('survey_pk')
        survey = get_object_or_404(Survey, pk=survey_id)
        
        # Проверяем, что пользователь является создателем опроса
        if survey.created_by != self.request.user and not self.request.user.is_superuser:
            return SurveyResponse.objects.none()
        
        return SurveyResponse.objects.filter(survey=survey) 