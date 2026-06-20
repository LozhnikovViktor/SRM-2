from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


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
        null=True,
        blank=True
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

    class Meta:
        verbose_name = "Тендер"
        verbose_name_plural = "Тендеры"
        ordering = ["-deadline"]

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
    """Модель клиента (покупателя)"""
    
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
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Менеджер',
        related_name='managed_clients',
        help_text='Пользователь системы, ведущий этого клиента'
    )
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


class TenderDocument(models.Model):
    """Документ, прикреплённый к тендеру"""
    
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Тендер'
    )
    file = models.FileField(
        'Файл',
        upload_to='tender_documents/%Y/%m/%d/',
        help_text='PDF, DOCX, JPG, PNG (макс. 10 МБ)'
    )
    name = models.CharField(
        'Название документа',
        max_length=200,
        help_text='Например: "Коммерческое предложение"'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        null=True,
        help_text='Краткое описание документа'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Загрузил',
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField('Загружен', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.name} ({self.tender.customer_name})"


class AuditLog(models.Model):
    """Лог действий пользователей"""
    
    ACTION_CHOICES = [
        ('create', 'Создание'),
        ('update', 'Обновление'),
        ('delete', 'Удаление'),
        ('login', 'Вход в систему'),
        ('logout', 'Выход из системы'),
        ('import', 'Импорт'),
        ('export', 'Экспорт'),
        ('view', 'Просмотр'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь',
        related_name='audit_logs'
    )
    action = models.CharField(
        'Действие',
        max_length=20,
        choices=ACTION_CHOICES
    )
    model_name = models.CharField(
        'Модель',
        max_length=100,
        help_text='Например: Tender, Client'
    )
    object_id = models.PositiveIntegerField(
        'ID объекта',
        null=True,
        blank=True,
        help_text='ID изменённого объекта'
    )
    object_repr = models.CharField(
        'Представление объекта',
        max_length=200,
        blank=True,
        help_text='Например: Название тендера'
    )
    changes = models.TextField(
        'Изменения',
        blank=True,
        null=True,
        help_text='JSON с описанием изменений'
    )
    ip_address = models.GenericIPAddressField(
        'IP-адрес',
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        'User Agent',
        blank=True,
        null=True
    )
    timestamp = models.DateTimeField(
        'Время',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Записи аудита'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()}: {self.model_name} #{self.object_id} ({self.timestamp})"
    
    def get_changes_dict(self):
        """Возвращает изменения как словарь"""
        import json
        if self.changes:
            try:
                return json.loads(self.changes)
            except:
                return {}
        return {}

class Comment(models.Model):
    """Комментарий к тендеру"""
    
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Тендер'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    text = models.TextField(
        'Текст комментария',
        help_text='Максимум 1000 символов'
    )
    created_at = models.DateTimeField(
        'Создан',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Обновлён',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Комментарий от {self.author.username} к {self.tender.customer_name}"
    




class ChatRoom(models.Model):
    """Комната чата (для тендера или клиента)"""
    ROOM_TYPE_CHOICES = [
        ('tender', 'Тендер'),
        ('client', 'Клиент'),
    ]
    
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES)
    tender = models.ForeignKey('Tender', on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    client = models.ForeignKey('Client', on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.room_type == 'tender' and self.tender:
            return f"Чат тендера: {self.tender.customer_name}"
        elif self.room_type == 'client' and self.client:
            return f"Чат клиента: {self.client.name}"
        return f"ChatRoom {self.id}"
    
    def get_last_message(self):
        return self.messages.order_by('-created_at').first()
    
    def unread_count(self, user):
        if not user.is_authenticated:
            return 0
        return self.messages.exclude(author=user).filter(
            read_by__isnull=True
        ).count()


class ChatMessage(models.Model):
    """Сообщение в чате"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"
    


    # ============================================
# 🔹 НОМЕНКЛАТУРА ПРОДУКЦИИ
# ============================================
class Product(models.Model):
    """Номенклатура продукции"""
    name = models.CharField('Наименование', max_length=200)
    article = models.CharField('Артикул', max_length=50, blank=True)
    price = models.DecimalField('Цена прайс', max_digits=12, decimal_places=2, default=0)
    unit = models.CharField('Ед. измерения', max_length=20, default='шт')
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Продукция'
        verbose_name_plural = 'Продукция'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.article} {self.name}" if self.article else self.name


# ============================================
# 🔹 ЗАЯВКА НА ОТГРУЗКУ
# ============================================
class ShipmentRequest(models.Model):
    """Заявка на отгрузку от покупателя"""
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('processing', 'В обработке'),
        ('approved', 'Согласована'),
        ('shipped', 'Отгружена'),
        ('cancelled', 'Отменена'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, 
                               related_name='shipment_requests', 
                               verbose_name='Покупатель')
    contact_person = models.CharField('Контактное лицо', max_length=200, blank=True)
    contact_phone = models.CharField('Телефон', max_length=50, blank=True)
    contact_email = models.EmailField('Email', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    comment = models.TextField('Комментарий', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                   null=True, blank=True, 
                                   related_name='created_shipment_requests',
                                   verbose_name='Кем создана')
    exported_to_1c = models.BooleanField('Выгружена в 1С', default=False)
    exported_at = models.DateTimeField('Дата выгрузки', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Заявка на отгрузку'
        verbose_name_plural = 'Заявки на отгрузку'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заявка #{self.id} от {self.client.name}"
    
    @property
    def total_amount(self):
        """Общая сумма заявки"""
        return sum(item.total for item in self.items.all())
    
    @property
    def total_quantity(self):
        """Общее количество"""
        return sum(item.quantity for item in self.items.all())


class ShipmentRequestItem(models.Model):
    """Позиция заявки на отгрузку"""
    request = models.ForeignKey(ShipmentRequest, on_delete=models.CASCADE, 
                                related_name='items', verbose_name='Заявка')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, 
                                related_name='shipment_items', 
                                verbose_name='Продукция')
    quantity = models.DecimalField('Количество', max_digits=12, decimal_places=3)
    unit_price = models.DecimalField('Цена за ед.', max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField('Скидка, %', max_digits=5, decimal_places=2, 
                                           default=0, help_text='Скидка от прайса в %')
    final_price = models.DecimalField('Итоговая цена', max_digits=12, decimal_places=2,
                                      help_text='Цена с учётом скидки')
    
    class Meta:
        verbose_name = 'Позиция заявки'
        verbose_name_plural = 'Позиции заявки'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total(self):
        """Сумма по позиции"""
        return self.final_price * self.quantity
    
    def save(self, *args, **kwargs):
        # Автоматически рассчитываем финальную цену
        if self.discount_percent:
            self.final_price = self.unit_price * (1 - self.discount_percent / 100)
        else:
            self.final_price = self.unit_price
        super().save(*args, **kwargs)