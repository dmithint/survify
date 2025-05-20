from django import forms
from .models import Survey, Question, Choice, Answer, AnswerChoice

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'privacy']
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'privacy': 'Приватность',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'required']
        labels = {
            'text': 'Текст вопроса',
            'question_type': 'Тип вопроса',
            'required': 'Обязательный',
        }
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text']
        labels = {
            'text': 'Вариант ответа',
        }
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control choice-text'}),
        }

ChoiceFormSet = forms.inlineformset_factory(
    Question, Choice,
    form=ChoiceForm,
    extra=2,
    can_delete=True
)

class AnswerTextForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text_answer']
        widgets = {
            'text_answer': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
        labels = {
            'text_answer': '',
        }

class AnswerRadioForm(forms.Form):
    answer = forms.ChoiceField(widget=forms.RadioSelect, required=False)

    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['answer'].choices = [(choice.id, choice.text) for choice in question.choices.all()]
        self.fields['answer'].required = question.required
        self.question = question

class AnswerCheckboxForm(forms.Form):
    answers = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['answers'].choices = [(choice.id, choice.text) for choice in question.choices.all()]
        self.fields['answers'].required = question.required
        self.question = question 