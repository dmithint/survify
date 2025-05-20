from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import (
    SurveyViewSet, QuestionViewSet, SurveyResponseAPIView,
    UserSurveyResponsesViewSet, SurveyResultsViewSet
)

router = DefaultRouter()
router.register(r'surveys', SurveyViewSet, basename='api-survey')
router.register(r'questions', QuestionViewSet, basename='api-question')
router.register(r'my-responses', UserSurveyResponsesViewSet, basename='api-my-responses')

urlpatterns = [
    path('', include(router.urls)),
    path('submit-response/', SurveyResponseAPIView.as_view(), name='api-submit-response'),
    path('surveys/<int:survey_pk>/results/', SurveyResultsViewSet.as_view({'get': 'list'}), name='api-survey-results'),
] 