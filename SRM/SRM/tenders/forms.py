from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Client
from .models import Tender, Client, TenderDocument, AuditLog, Comment


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


class ClientForm(forms.ModelForm):
    #Форма для создания/редактирования клиента"""
    
    class Meta:
        model = Client
        fields = [
            'name', 'inn', 'email', 'phone', 
            'contact_person', 'contact_position',
            'manager', 'address', 'website', 
            'notes', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ООО "Ромашка"'}),
            'inn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890', 'maxlength': '12'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'info@company.ru'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'contact_position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Директор'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://company.ru'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'Наименование организации',
            'inn': 'ИНН',
            'email': 'Email',
            'phone': 'Телефон',
            'contact_person': 'Контактное лицо',
            'contact_position': 'Должность контактного лица',
            'manager': 'Менеджер',
            'address': 'Адрес',
            'website': 'Сайт',
            'notes': 'Примечания',
            'status': 'Статус',
        }
    
    def clean_inn(self):
        inn = self.cleaned_data.get('inn')
        if inn and not inn.isdigit():
            raise forms.ValidationError('ИНН должен содержать только цифры')
        if inn and len(inn) not in (10, 12):
            raise forms.ValidationError('ИНН должен содержать 10 или 12 цифр')
        return inn
    
class TenderForm(forms.ModelForm):
    #Форма для создания/редактирования тендера"""
    
    class Meta:
        model = Tender
        fields = [
            'client', 'customer_name', 'initial_amount', 'deadline', 
            'status', 'executor_name', 'procedure_url',
            'winner', 'final_amount', 'cost', 'comment'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название организации'}),
            'initial_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'executor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО исполнителя'}),
            'procedure_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'winner': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Победитель'}),
            'final_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
        }
        labels = {
            'client': 'Клиент',
            'customer_name': 'Заказчик',
            'initial_amount': 'Начальная сумма',
            'deadline': 'Дедлайн',
            'status': 'Статус',
            'executor_name': 'Исполнитель',
            'procedure_url': 'Ссылка на процедуру',
            'winner': 'Победитель',
            'final_amount': 'Итоговая сумма',
            'cost': 'Себестоимость',
            'comment': 'Комментарий',
        }


class TenderDocumentForm(forms.ModelForm):
    """Форма для загрузки документа к тендеру"""
    
    class Meta:
        model = TenderDocument
        fields = ['name', 'file', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Коммерческое предложение'
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.zip,.rar'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '2',
                'placeholder': 'Краткое описание (необязательно)'
            }),
        }
        labels = {
            'name': 'Название документа',
            'file': 'Файл',
            'description': 'Описание',
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Проверка размера
            if file.size > TenderDocument.MAX_FILE_SIZE:
                raise forms.ValidationError(
                    f'Размер файла не должен превышать 10 МБ. '
                    f'Ваш файл: {round(file.size / (1024*1024), 2)} МБ'
                )
            
            # Проверка расширения
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in TenderDocument.ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f'Недопустимый формат файла: {ext}. '
                    f'Разрешены: {", ".join(TenderDocument.ALLOWED_EXTENSIONS)}'
                )
        
        return file

class TenderFilterForm(forms.Form):
    """Форма расширенного поиска и фильтрации тендеров"""
    
    # Текстовый поиск
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '🔍 Поиск по названию, заказчику, ИНН...'
        })
    )
    
    # Статус (мульти-выбор)
    status = forms.MultipleChoiceField(
        required=False,
        choices=[
            ('draft', 'Черновик'),
            ('submitted', 'Подан'),
            ('published', 'Опубликован'),
            ('won', 'Выигран'),
            ('lost', 'Проигран'),
            ('cancelled', 'Отменён'),
        ],
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '6'
        })
    )
    
    # Диапазон сумм
    amount_from = forms.DecimalField(
        required=False,
        label='Сумма от',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'step': '1000'
        })
    )
    
    amount_to = forms.DecimalField(
        required=False,
        label='Сумма до',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '∞',
            'step': '1000'
        })
    )
    
    # Диапазон дат
    deadline_from = forms.DateField(
        required=False,
        label='Дедлайн от',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    deadline_to = forms.DateField(
        required=False,
        label='Дедлайн до',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    # Клиент
    client = forms.ModelChoiceField(
        required=False,
        queryset=Client.objects.all(),
        label='Клиент',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # Исполнитель
    executor = forms.CharField(
        required=False,
        label='Исполнитель',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя исполнителя'
        })
    )
    
    # Сортировка
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('-deadline', 'Дедлайн (сначала ближайшие)'),
            ('deadline', 'Дедлайн (сначала дальние)'),
            ('-initial_amount', 'Сумма (по убыванию)'),
            ('initial_amount', 'Сумма (по возрастанию)'),
            ('-created_at', 'Дата создания (новые)'),
            ('created_at', 'Дата создания (старые)'),
            ('customer_name', 'Название заказчика (А-Я)'),
            ('-customer_name', 'Название заказчика (Я-А)'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # Быстрые фильтры (чекбоксы)
    urgent_only = forms.BooleanField(
        required=False,
        label='Только срочные (24 часа)',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    overdue_only = forms.BooleanField(
        required=False,
        label='Только просроченные',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    has_documents = forms.BooleanField(
        required=False,
        label='Только с документами',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

class CommentForm(forms.ModelForm):
    """Форма добавления комментария"""
    
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Напишите комментарий...',
                'maxlength': '1000'
            })
        }