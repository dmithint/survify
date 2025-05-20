from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, ProfileForm
from surveys.models import Survey, SurveyResponse
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

@csrf_exempt
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(email=email, password=raw_password)
            login(request, user)
            messages.success(request, f'Аккаунт создан! Вы успешно вошли в систему.')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('profile')
    else:
        profile_form = ProfileForm(instance=request.user.profile)

    # Получаем опросы, созданные пользователем
    created_surveys = Survey.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Получаем опросы, в которых участвовал пользователь
    participated_surveys = Survey.objects.filter(
        responses__user=request.user
    ).exclude(
        created_by=request.user
    ).distinct().order_by('-responses__submitted_at')

    context = {
        'profile_form': profile_form,
        'created_surveys': created_surveys,
        'participated_surveys': participated_surveys,
    }
    
    return render(request, 'accounts/profile.html', context)
