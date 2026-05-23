from django.views.generic import ListView, CreateView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Tender
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'tenders/register.html'
    success_url = reverse_lazy('tenders:list')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)  # Автоматический вход после регистрации
        return super().form_valid(form)

class TenderListView(LoginRequiredMixin, ListView):
    model = Tender
    template_name = 'tenders/tender_list.html'
    context_object_name = 'tenders'
    ordering = ['-deadline']

    def get_queryset(self):
        # Возвращаем ВСЕ тендеры, а не только свои
        queryset = Tender.objects.all()
        
        # Фильтрация по параметрам URL (поиск) остается
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
        'customer_name', 'initial_amount', 'deadline', 'executor_name', 'procedure_url',
        'winner', 'final_amount', 'cost'
    ]
    template_name = 'tenders/tender_form.html'
    success_url = reverse_lazy('tenders:list')

    def form_valid(self, form):
        # Явно присваиваем текущего пользователя автором перед сохранением
        form.instance.author = self.request.user
        return super().form_valid(form)

class TenderDeleteView(LoginRequiredMixin, DeleteView):
    model = Tender
    template_name = 'tenders/tender_confirm_delete.html'
    success_url = reverse_lazy('tenders:list')

class TenderUpdateView(LoginRequiredMixin, UpdateView):
    model = Tender
    fields = [
        'customer_name', 'initial_amount', 'deadline', 'executor_name', 'procedure_url',
        'winner', 'final_amount', 'cost'
    ]
    template_name = 'tenders/tender_form.html'  # Используем тот же шаблон, что и для создания
    success_url = reverse_lazy('tenders:list')