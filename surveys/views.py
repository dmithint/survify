from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, Http404
from django.db import transaction
from django.forms import formset_factory
from django.urls import reverse
from .models import Survey, Question, Choice, Answer, AnswerChoice, SurveyResponse
from .forms import SurveyForm, QuestionForm, ChoiceFormSet, AnswerTextForm, AnswerRadioForm, AnswerCheckboxForm

def home(request):
    # Показываем публичные опросы
    public_surveys = Survey.objects.filter(privacy='public').order_by('-created_at')
    
    context = {
        'surveys': public_surveys
    }
    
    return render(request, 'surveys/home.html', context)

@login_required
def survey_create(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user
            survey.save()
            messages.success(request, 'Опрос успешно создан! Теперь добавьте вопросы.')
            return redirect('survey_edit', pk=survey.id)
    else:
        form = SurveyForm()
    
    return render(request, 'surveys/survey_form.html', {'form': form})

@login_required
def survey_edit(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    
    # Проверяем, что редактирует владелец опроса
    if survey.created_by != request.user:
        return HttpResponseForbidden("У вас нет прав для редактирования этого опроса")
    
    if request.method == 'POST':
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, 'Опрос успешно обновлен!')
            return redirect('survey_edit', pk=survey.id)
    else:
        form = SurveyForm(instance=survey)
    
    questions = survey.questions.all().order_by('order')
    
    return render(request, 'surveys/survey_edit.html', {
        'form': form,
        'survey': survey,
        'questions': questions
    })

@login_required
def survey_delete(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    
    # Проверяем, что удаляет владелец опроса
    if survey.created_by != request.user:
        return HttpResponseForbidden("У вас нет прав для удаления этого опроса")
    
    if request.method == 'POST':
        survey.delete()
        messages.success(request, 'Опрос успешно удален!')
        return redirect('profile')
    
    return render(request, 'surveys/survey_confirm_delete.html', {'survey': survey})

@login_required
def question_create(request, survey_id):
    survey = get_object_or_404(Survey, pk=survey_id)
    
    # Проверяем, что вопрос создает владелец опроса
    if survey.created_by != request.user:
        return HttpResponseForbidden("У вас нет прав для добавления вопросов в этот опрос")
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        
        if question_form.is_valid():
            with transaction.atomic():
                question = question_form.save(commit=False)
                question.survey = survey
                question.order = survey.questions.count() + 1
                question.save()
                
                # Если тип вопроса предполагает варианты ответов
                if question.question_type in ['radio', 'checkbox']:
                    formset = ChoiceFormSet(request.POST, instance=question)
                    if formset.is_valid():
                        formset.save()
                
                messages.success(request, 'Вопрос успешно добавлен!')
                return redirect('survey_edit', pk=survey.id)
    else:
        question_form = QuestionForm()
        formset = ChoiceFormSet()
    
    return render(request, 'surveys/question_form.html', {
        'question_form': question_form,
        'formset': formset,
        'survey': survey
    })

@login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk)
    survey = question.survey
    
    # Проверяем, что вопрос редактирует владелец опроса
    if survey.created_by != request.user:
        return HttpResponseForbidden("У вас нет прав для редактирования этого вопроса")
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST, instance=question)
        
        if question_form.is_valid():
            with transaction.atomic():
                question_form.save()
                
                # Если тип вопроса предполагает варианты ответов
                if question.question_type in ['radio', 'checkbox']:
                    formset = ChoiceFormSet(request.POST, instance=question)
                    if formset.is_valid():
                        formset.save()
                
                messages.success(request, 'Вопрос успешно обновлен!')
                return redirect('survey_edit', pk=survey.id)
    else:
        question_form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)
    
    return render(request, 'surveys/question_form.html', {
        'question_form': question_form,
        'formset': formset,
        'survey': survey,
        'question': question
    })

@login_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    survey = question.survey
    
    # Проверяем, что вопрос удаляет владелец опроса
    if survey.created_by != request.user:
        return HttpResponseForbidden("У вас нет прав для удаления этого вопроса")
    
    if request.method == 'POST':
        # Сохраняем порядок вопроса для последующего обновления порядка оставшихся вопросов
        question_order = question.order
        
        # Удаляем вопрос
        question.delete()
        
        # Обновляем порядок оставшихся вопросов
        for q in survey.questions.filter(order__gt=question_order):
            q.order -= 1
            q.save()
        
        messages.success(request, 'Вопрос успешно удален!')
        return redirect('survey_edit', pk=survey.id)
    
    return render(request, 'surveys/question_confirm_delete.html', {
        'question': question,
        'survey': survey
    })

def survey_detail(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    
    # Проверяем доступность опроса
    if survey.privacy == 'authenticated' and not request.user.is_authenticated:
        messages.warning(request, 'Для прохождения этого опроса необходимо войти в систему')
        return redirect('login')
    
    # Если пользователь аутентифицирован, проверяем, не проходил ли он уже этот опрос
    if request.user.is_authenticated:
        already_responded = SurveyResponse.objects.filter(
            survey=survey,
            user=request.user
        ).exists()
        
        # Владелец всегда может просматривать свой опрос
        is_owner = survey.created_by == request.user
    else:
        already_responded = False
        is_owner = False
    
    context = {
        'survey': survey,
        'questions': survey.questions.all().order_by('order'),
        'already_responded': already_responded,
        'is_owner': is_owner
    }
    
    return render(request, 'surveys/survey_detail.html', context)

def survey_take(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    
    # Проверяем доступность опроса
    if survey.privacy == 'authenticated' and not request.user.is_authenticated:
        messages.warning(request, 'Для прохождения этого опроса необходимо войти в систему')
        return redirect('login')
    
    # Если пользователь аутентифицирован, проверяем, не проходил ли он уже этот опрос
    if request.user.is_authenticated:
        already_responded = SurveyResponse.objects.filter(
            survey=survey,
            user=request.user
        ).exists()
        
        if already_responded:
            messages.warning(request, 'Вы уже проходили этот опрос')
            return redirect('survey_detail', pk=survey.id)
    
    questions = survey.questions.all().order_by('order')
    
    if request.method == 'POST':
        forms_valid = True
        
        # Создаем ответ на опрос
        with transaction.atomic():
            # Создаем запись об ответе на опрос
            survey_response = SurveyResponse.objects.create(
                survey=survey,
                user=request.user if request.user.is_authenticated else None
            )
            
            # Обрабатываем ответы на каждый вопрос
            for question in questions:
                if question.question_type == 'text':
                    form = AnswerTextForm(request.POST, prefix=f'question_{question.id}')
                    if form.is_valid():
                        answer = form.save(commit=False)
                        answer.question = question
                        answer.user = request.user if request.user.is_authenticated else None
                        answer.anonymous_user = None if request.user.is_authenticated else survey_response.anonymous_user
                        answer.save()
                    else:
                        forms_valid = False
                
                elif question.question_type == 'radio':
                    form = AnswerRadioForm(question, request.POST, prefix=f'question_{question.id}')
                    if form.is_valid() and form.cleaned_data['answer']:
                        answer = Answer.objects.create(
                            question=question,
                            user=request.user if request.user.is_authenticated else None,
                            anonymous_user=None if request.user.is_authenticated else survey_response.anonymous_user
                        )
                        choice_id = form.cleaned_data['answer']
                        AnswerChoice.objects.create(
                            answer=answer,
                            choice_id=choice_id
                        )
                    elif question.required:
                        forms_valid = False
                
                elif question.question_type == 'checkbox':
                    form = AnswerCheckboxForm(question, request.POST, prefix=f'question_{question.id}')
                    if form.is_valid() and (not question.required or form.cleaned_data['answers']):
                        answer = Answer.objects.create(
                            question=question,
                            user=request.user if request.user.is_authenticated else None,
                            anonymous_user=None if request.user.is_authenticated else survey_response.anonymous_user
                        )
                        for choice_id in form.cleaned_data['answers']:
                            AnswerChoice.objects.create(
                                answer=answer,
                                choice_id=choice_id
                            )
                    elif question.required:
                        forms_valid = False
        
        if forms_valid:
            messages.success(request, 'Спасибо за прохождение опроса!')
            return redirect('survey_detail', pk=survey.id)
        else:
            # Если какие-то формы не прошли валидацию, удаляем созданный ответ на опрос
            survey_response.delete()
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    
    # Создаем формы для каждого вопроса
    forms = []
    for question in questions:
        if question.question_type == 'text':
            form = AnswerTextForm(prefix=f'question_{question.id}')
        elif question.question_type == 'radio':
            form = AnswerRadioForm(question, prefix=f'question_{question.id}')
        elif question.question_type == 'checkbox':
            form = AnswerCheckboxForm(question, prefix=f'question_{question.id}')
        
        forms.append((question, form))
    
    context = {
        'survey': survey,
        'forms': forms
    }
    
    return render(request, 'surveys/survey_take.html', context)

@login_required
def survey_results(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    
    # Только создатель опроса может видеть результаты
    if survey.created_by != request.user:
        return HttpResponseForbidden("У вас нет прав для просмотра результатов этого опроса")
    
    # Получаем все ответы на опрос
    responses = survey.responses.all().order_by('-submitted_at')
    
    # Получаем статистику по каждому вопросу
    questions_data = []
    for question in survey.questions.all().order_by('order'):
        question_data = {
            'question': question,
            'answers': []
        }
        
        # Для вопросов с выбором вариантов считаем количество каждого выбора
        if question.question_type in ['radio', 'checkbox']:
            # Получаем все ответы на этот вопрос
            answers = Answer.objects.filter(question=question)
            total_responses = answers.count()
            
            # Для checkbox (множественный выбор) процент должен показывать долю ответивших,
            # выбравших данный вариант. Для radio (один вариант) - долю выбравших данный вариант
            # от общего числа ответов на вопрос.
            
            choices = {}
            for choice in question.choices.all():
                # Сколько раз был выбран этот вариант
                choice_count = AnswerChoice.objects.filter(
                    answer__question=question,
                    choice=choice
                ).count()
                
                choices[choice.id] = {
                    'text': choice.text,
                    'count': choice_count,
                    'percentage': (choice_count / total_responses * 100) if total_responses > 0 else 0
                }
            
            question_data['choices'] = [v for k, v in choices.items()]
            question_data['total_responses'] = total_responses
        
        # Для текстовых вопросов просто получаем все текстовые ответы
        if question.question_type == 'text':
            answers = question.answers.all()
            question_data['text_answers'] = answers
        
        questions_data.append(question_data)
    
    context = {
        'survey': survey,
        'responses': responses,
        'questions_data': questions_data
    }
    
    return render(request, 'surveys/survey_results.html', context)

def survey_by_link(request, short_code):
    survey = get_object_or_404(Survey, short_code=short_code)
    
    # Проверяем доступность опроса
    if survey.privacy == 'authenticated' and not request.user.is_authenticated:
        messages.warning(request, 'Для прохождения этого опроса необходимо войти в систему')
        return redirect('login')
    
    return redirect('survey_detail', pk=survey.id)
