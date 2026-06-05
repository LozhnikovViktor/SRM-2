from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label='Email',
        required=True,
        help_text='Обязательное поле. Введите ваш email для получения уведомлений.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email


class SearchTenderForm(forms.Form):
    """Форма для поиска тендеров на zakupki.gov.ru"""
    
    keyword = forms.CharField(
        label='Ключевое слово',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: компьютеры, строительство, медицина'
        })
    )
    
    region = forms.ChoiceField(
        label='Регион (необязательно)',
        required=False,
        choices=[
            ('', 'Все регионы'),
            ('1', 'Республика Адыгея'),
            ('2', 'Республика Башкортостан'),
            ('3', 'Республика Бурятия'),
            ('77', 'г. Москва'),
            ('78', 'г. Санкт-Петербург'),
            ('50', 'Московская область'),
            ('47', 'Ленинградская область'),
            ('23', 'Краснодарский край'),
            ('63', 'Самарская область'),
            ('54', 'Новосибирская область'),
            ('66', 'Свердловская область'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    max_results = forms.IntegerField(
        label='Максимум результатов',
        initial=20,
        min_value=5,
        max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )