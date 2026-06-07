# tenders/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class TenderStatus(models.TextChoices):
    DRAFT = 'draft', '📝 Черновик'
    SUBMITTED = 'submitted', '📤 Подан'
    WON = 'won', '✅ Выигран'
    LOST = 'lost', '❌ Проигран'
    CANCELLED = 'cancelled', '⚪ Отменён'

class Tender(models.Model):
    customer_name = models.CharField(max_length=255, verbose_name="Название заказчика")
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='tenders',
        verbose_name="Автор"
    )
     
    client = models.ForeignKey(
        'Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Клиент',
        related_name='tenders',
        help_text='Привязанный клиент (покупатель)'
    )
    initial_amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Начальная сумма контракта (₽)"
    )
    deadline = models.DateTimeField(
    verbose_name="Дата окончания подачи заявок",
    null=True,      # ← добавили: разрешаем NULL в базе данных
    blank=True      # ← добавили: разрешаем пустое значение в формах
)
    executor_name = models.CharField(max_length=255, verbose_name="ФИО исполнителя")
    procedure_url = models.URLField(verbose_name="Ссылка на процедуру")
    
    winner = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Победитель"
    )
    final_amount = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, 
        verbose_name="Сумма заключаемого контракта (₽)"
    )
    cost = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, 
        verbose_name="Себестоимость (₽)"
    )
    status = models.CharField(
        max_length=20,
        choices=TenderStatus.choices,
        default=TenderStatus.DRAFT,
        verbose_name='Статус'
    )
    comment = models.TextField(
        'Комментарий', 
        blank=True, 
        null=True,
        help_text='Дополнительная информация по тендеру'
    )
    # Добавьте в конец модели Tender (перед class Meta, если он есть)
    source_url = models.URLField(
        'Ссылка на источник',
        blank=True,
        null=True,
        help_text='URL на торговой площадке'
)
    external_id = models.CharField(
        'ID на площадке',
        max_length=50,
        blank=True,
        null=True,
        help_text='Уникальный номер закупки'
)

    def get_status_badge_class(self):
        colors = {
            'draft': 'secondary',
            'submitted': 'info',
            'won': 'success',
            'lost': 'danger',
            'cancelled': 'light text-dark',
        }
        return colors.get(self.status, 'secondary')


    class Meta:
        verbose_name = "Тендер"
        verbose_name_plural = "Тендеры"
        ordering = ["-deadline"]
        pass


    def clean(self):
        super().clean()
        if self.final_amount is not None and self.cost is not None:
            if self.cost > self.final_amount:
                raise ValidationError({
                    "cost": _("Себестоимость не может превышать сумму заключаемого контракта.")
                })

    @property
    def profit(self):
        if self.final_amount is not None and self.cost is not None:
            return self.final_amount - self.cost
        return None

    @property
    def markup(self):
        if self.cost and self.cost != 0 and self.profit is not None:
            return (self.profit / self.cost) * 100
        return None

    def __str__(self):
        return f"{self.customer_name} | {self.initial_amount:,.2f} ₽"
class Client(models.Model):
    #Модель клиента (покупателя)
  
    
    # Основная информация
        name = models.CharField(
        'Наименование',
        max_length=200,
        help_text='Полное наименование организации'
    )
        inn = models.CharField(
        'ИНН',
        max_length=12,
        unique=True,
        help_text='10 цифр для юрлиц, 12 для ИП'
    )
    
    # Контактная информация
        email = models.EmailField(
        'Email',
        blank=True,
        null=True,
        help_text='Основной email организации'
    )
        phone = models.CharField(
        'Телефон',
        max_length=20,
        blank=True,
        null=True,
        help_text='Основной телефон организации'
    )
        contact_person = models.CharField(
        'Контактное лицо',
        max_length=200,
        blank=True,
        null=True,
        help_text='ФИО контактного лица'
    )
        contact_position = models.CharField(
        'Должность контактного лица',
        max_length=100,
        blank=True,
        null=True
    )
    
    # Менеджер, ведущий клиента
        manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Менеджер',
        related_name='managed_clients',
        help_text='Пользователь системы, ведущий этого клиента'
    )
    
    # Дополнительная информация
        address = models.TextField(
        'Адрес',
        blank=True,
        null=True
    )
        website = models.URLField(
        'Сайт',
        blank=True,
        null=True,
        max_length=200
    )
        notes = models.TextField(
        'Примечания',
        blank=True,
        null=True,
        help_text='Дополнительная информация о клиенте'
    )
    
    # Статус и даты
        STATUS_CHOICES = [
        ('prospect', '🔍 Потенциальный'),
        ('active', '✅ Активный'),
        ('inactive', '⏸️ Неактивный'),
        ('blacklist', '🚫 В чёрном списке'),
    ]
        status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='prospect'
    )
    
        created_at = models.DateTimeField('Создан', auto_now_add=True)
        updated_at = models.DateTimeField('Обновлён', auto_now=True)
        created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Кем создан',
        related_name='created_clients'
    )
    
        class Meta:
            verbose_name = 'Клиент'
            verbose_name_plural = 'Клиенты'
            ordering = ['-updated_at']
    
        def __str__(self):
            return f"{self.name} (ИНН: {self.inn})"