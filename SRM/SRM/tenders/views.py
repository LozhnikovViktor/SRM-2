# tenders/views.py
from django.shortcuts import render
from django.db.models import F, Sum, Count, Avg, Q, ExpressionWrapper, DecimalField
from django.views.generic import ListView, CreateView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from .utils import export_tenders_to_excel, export_dashboard_stats_to_excel

from .models import Tender

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'tenders/register.html'
    success_url = reverse_lazy('tenders:list')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)

class TenderListView(LoginRequiredMixin, ListView):
    model = Tender
    template_name = 'tenders/tender_list.html'
    context_object_name = 'tenders'
    ordering = ['-deadline']
    paginate_by = 5

    def get_queryset(self):
        queryset = Tender.objects.all()
        customer = self.request.GET.get('customer')
        winner = self.request.GET.get('winner')
        executor = self.request.GET.get('executor')

        if customer:
            queryset = queryset.filter(customer_name__icontains=customer)
        if winner:
            if winner == 'empty':
                queryset = queryset.filter(winner__isnull=True) | queryset.filter(winner='')
            elif winner == 'filled':
                queryset = queryset.exclude(winner__isnull=True).exclude(winner='')
        if executor:
            queryset = queryset.filter(executor_name__icontains=executor)
        return queryset

class TenderCreateView(LoginRequiredMixin, CreateView):
    model = Tender
    fields = [
        'customer_name', 'initial_amount', 'deadline', 'status', 'executor_name', 'procedure_url',
        'winner', 'final_amount', 'cost'
    ]
    template_name = 'tenders/tender_form.html'
    success_url = reverse_lazy('tenders:list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class TenderDeleteView(LoginRequiredMixin, DeleteView):
    model = Tender
    template_name = 'tenders/tender_confirm_delete.html'
    success_url = reverse_lazy('tenders:list')

class TenderUpdateView(LoginRequiredMixin, UpdateView):
    model = Tender
    fields = [
        'customer_name', 'initial_amount', 'deadline', 'status', 'executor_name', 'procedure_url',
        'winner', 'final_amount', 'cost'
    ]
    template_name = 'tenders/tender_form.html'
    success_url = reverse_lazy('tenders:list')

def dashboard(request):
    """Дашборд со статистикой"""
    now = timezone.now()
    six_months_ago = now - timedelta(days=180)
    
    # 1. Считаем общее количество и выигранные
    total_tenders = Tender.objects.count()
    won_tenders = Tender.objects.filter(status='won').count()
    # Активные = отправленные или опубликованные
    active_tenders = Tender.objects.filter(status__in=['submitted', 'published']).count() 
    
    # Конверсия (в процентах)
    conversion = round((won_tenders / total_tenders * 100), 1) if total_tenders > 0 else 0
    
    # 2. Расчет прибыли и наценки (только для выигранных 'won')
    won_qs = Tender.objects.filter(status='won')
    
    # Собираем суммы (если полей нет, берем 0)
    totals = won_qs.aggregate(
        total_final=Sum('final_amount'),
        total_cost=Sum('cost')
    )
    total_final = totals['total_final'] or 0
    total_cost = totals['total_cost'] or 0
    
    profit = total_final - total_cost
    
    # Наценка в процентах
    if total_cost > 0:
        markup_percent = round((profit / total_cost) * 100, 1)
    else:
        markup_percent = 0

    # 3. График: тендеры по месяцам
    from collections import defaultdict
    
    tenders_qs = Tender.objects.filter(
        deadline__isnull=False,
        deadline__gte=six_months_ago
    ).values('deadline', 'status')
    
    monthly_data = defaultdict(lambda: {'total': 0, 'won': 0})
    for t in tenders_qs:
        month = t['deadline'].strftime('%Y-%m')
        monthly_data[month]['total'] += 1
        if t['status'] == 'won':
            monthly_data[month]['won'] += 1
    
    monthly_stats = [
        {'month': month, 'total': data['total'], 'won': data['won']}
        for month, data in sorted(monthly_data.items())
    ]
    
    # 4. Ближайшие дедлайны (только для активных)
    upcoming_deadlines = Tender.objects.filter(
        deadline__gte=now,
    ).order_by('deadline')[:5]
    
    # 5. Собираем контекст и отдаем в шаблон
    context = {
    'total_tenders': total_tenders,
    'active_tenders': active_tenders,
    'won_tenders': won_tenders,
    'win_rate': conversion,  # ← изменили с 'conversion' на 'win_rate'
    'total_profit': profit,  # ← изменили с 'profit' на 'total_profit'
    'avg_markup': markup_percent,  # ← изменили с 'markup_percent' на 'avg_markup'
    'monthly_stats': monthly_stats,
    'upcoming_deadlines': upcoming_deadlines,
}
    
    return render(request, 'tenders/dashboard.html', context)
def export_tenders_excel(request):
    """Экспорт всех тендеров в Excel"""
    tenders_qs = Tender.objects.all().order_by('-deadline')
    excel_file = export_tenders_to_excel(tenders_qs)
    
    response = HttpResponse(
        excel_file,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=tenders_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return response


def export_dashboard_excel(request):
    """Экспорт статистики дашборда в Excel"""
    excel_file = export_dashboard_stats_to_excel()
    
    response = HttpResponse(
        excel_file,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=dashboard_stats_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return response