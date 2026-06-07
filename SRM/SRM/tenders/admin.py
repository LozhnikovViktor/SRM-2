# tender/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Tender
from .models import Tender, Client


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    # ➕ Добавили status_colored в начало списка
    list_display = (
        "status_colored",
        "customer_name",
        "initial_amount",
        "deadline",
        "author",
        "executor_name",
        "winner",
        "final_amount",
        "cost",
        "profit_display",
        "markup_display",
        "procedure_link",
    )
    # ➕ Добавили "status" в фильтры
    list_filter = (
        "status",
        "author",
        "winner",
        "deadline",
        "executor_name"
    )
    search_fields = ("customer_name", "executor_name", "winner")
    date_hierarchy = "deadline"
    ordering = ["-deadline"]

    readonly_fields = ("profit_display", "markup_display", "procedure_link")

    # ➕ Добавили "status" в первую секцию fieldsets
    fieldsets = (
        ("📄 Основная информация", {
            "fields": ("customer_name", "initial_amount", "deadline", "status", "executor_name", "procedure_url")
        }),
        ("🏁 Итоги процедуры", {
            "fields": ("winner", "final_amount", "cost")
        }),
        ("📊 Расчетные показатели", {
            "fields": ("profit_display", "markup_display", "procedure_link"),
            "classes": ("collapse",),
            "description": "Поля рассчитываются автоматически на основе суммы контракта и себестоимости."
        }),
    )

    @admin.display(description="Валовая прибыль")
    def profit_display(self, obj):
        return f"{obj.profit:,.2f} ₽" if obj.profit is not None else "—"

    @admin.display(description="Наценка, %")
    def markup_display(self, obj):
        return f"{obj.markup:,.2f} %" if obj.markup is not None else "—"

    @admin.display(description="Ссылка на процедуру")
    def procedure_link(self, obj):
        if obj.procedure_url:
            return format_html('<a href="{}" target="_blank" class="button">Открыть ↗</a>', obj.procedure_url)
        return "—"

    # ➕ НОВЫЙ МЕТОД: Цветной статус для списка в админке
    @admin.display(description="Статус", ordering="status")
    def status_colored(self, obj):
        colors = {
            'draft': '#6c757d',    # 📝 Серый
            'submitted': '#0dcaf0', # 📤 Голубой
            'won': '#198754',      # ✅ Зелёный
            'lost': '#dc3545',     # ❌ Красный
            'cancelled': '#f8f9fa', # ⚪ Светлый
        }
        color = colors.get(obj.status, '#6c757d')
        # get_status_display() автоматически подтянет человекочитаемое название из TextChoices
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display()
        )

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.author:
            obj.author = request.user
        obj.full_clean()
        super().save_model(request, obj, form, change)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'email', 'manager', 'status', 'updated_at')
    list_filter = ('status', 'manager', 'created_at')
    search_fields = ('name', 'inn', 'email', 'contact_person')
    list_editable = ('status', 'manager')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'inn', 'status')
        }),
        ('Контактная информация', {
            'fields': ('email', 'phone', 'contact_person', 'contact_position', 'website', 'address')
        }),
        ('Менеджер и примечания', {
            'fields': ('manager', 'notes')
        }),
        ('Системная информация', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если объект создаётся
            obj.created_by = request.user
        super().save_model(request, obj, form, change)