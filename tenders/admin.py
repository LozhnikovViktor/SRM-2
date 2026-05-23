from django.contrib import admin
from django.utils.html import format_html
from .models import Tender


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = (
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
    list_filter = ("author","winner", "deadline", "executor_name")
    search_fields = ("customer_name", "executor_name", "winner")
    date_hierarchy = "deadline"
    ordering = ["-deadline"]

    readonly_fields = ("profit_display", "markup_display", "procedure_link")

    fieldsets = (
        ("📄 Основная информация", {
            "fields": ("customer_name", "initial_amount", "deadline", "executor_name", "procedure_url")
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

    def save_model(self, request, obj, form, change):
        # Если создаем новый тендер в админке и автор не указан, ставим текущего админа
        if not obj.pk and not obj.author:
            obj.author = request.user
        obj.full_clean()
        super().save_model(request, obj, form, change)