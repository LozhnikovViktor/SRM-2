from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Tender(models.Model):
    customer_name = models.CharField(max_length=255, verbose_name="Название заказчика")
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='tenders',
        verbose_name="Автор"
    )
    initial_amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Начальная сумма контракта (₽)"
    )
    deadline = models.DateTimeField(verbose_name="Дата окончания подачи заявок")
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

    class Meta:
        verbose_name = "Тендер"
        verbose_name_plural = "Тендеры"
        ordering = ["-deadline"]

    def clean(self):
        """Валидация: себестоимость не может превышать итоговую сумму."""
        super().clean()
        if self.final_amount is not None and self.cost is not None:
            if self.cost > self.final_amount:
                raise ValidationError({
                    "cost": _("Себестоимость не может превышать сумму заключаемого контракта.")
                })

    @property
    def profit(self):
        """Валовая прибыль = Сумма контракта - Себестоимость."""
        if self.final_amount is not None and self.cost is not None:
            return self.final_amount - self.cost
        return None

    @property
    def markup(self):
        """Наценка в % = (Прибыль / Себестоимость) * 100."""
        if self.cost and self.cost != 0 and self.profit is not None:
            return (self.profit / self.cost) * 100
        return None

    def __str__(self):
        return f"{self.customer_name} | {self.initial_amount:,.2f} ₽"