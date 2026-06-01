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
    
    # ... (статистика, прибыль, наценка — без изменений) ...
    
    # 📈 График: тендеры по месяцам (группировка в Python)
    from collections import defaultdict  # ❌ Лучше убрать отсюда, если уже импортировано вверху
    
    six_months_ago = now - timedelta(days=180)
    
    # 1. Получаем сырые данные
    tenders_qs = Tender.objects.filter(
        deadline__isnull=False,
        deadline__gte=six_months_ago
    ).values('deadline', 'status')
    
    # 2. Группируем по месяцам в Python
    monthly_data = defaultdict(lambda: {'total': 0, 'won': 0})
    for t in tenders_qs:
        month = t['deadline'].strftime('%Y-%m')
        monthly_data[month]['total'] += 1
        if t['status'] == 'won':
            monthly_data[month]['won'] += 1
    
    # 3. Преобразуем в список для шаблона
    monthly_stats = [
        {'month': month, 'total': data['total'], 'won': data['won']}
        for month, data in sorted(monthly_data.items())
    ]
    
    # ... (дедлайны и контекст) ...
    
    context = {
        # ... другие переменные ...
        'monthly_stats': monthly_stats,  # 🔹 Передаём в шаблон
        # ...
    }
    
    return render(request, 'tenders/dashboard.html', context)  # 🔹 Один return в конце