# tenders/views.py
import json
from django.shortcuts import render, redirect
from django.db.models import F, Sum, Count, Avg, Q, ExpressionWrapper, DecimalField
from django.db import models as db_models  # ← Добавлено для models.Q
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User  # ← Добавлено для User.objects
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from collections import defaultdict
from .forms import CustomUserCreationForm, SearchTenderForm, ClientForm, TenderForm, TenderDocumentForm
from .forms import TenderForm
from .models import AuditLog


# Импорты из приложения

from .utils import export_tenders_to_excel, export_dashboard_stats_to_excel, search_tenders_on_zakupki
from .models import Tender, Client, TenderDocument


# ============================================
# 🔹 АВТОРИЗАЦИЯ
# ============================================
class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'tenders/register.html'
    success_url = reverse_lazy('tenders:list')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


# ============================================
# 🔹 ТЕНДЕРЫ
# ============================================
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
                queryset = queryset.filter(Q(winner__isnull=True) | Q(winner=''))
            elif winner == 'filled':
                queryset = queryset.exclude(winner__isnull=True).exclude(winner='')
        if executor:
            queryset = queryset.filter(executor_name__icontains=executor)
        return queryset


class TenderCreateView(LoginRequiredMixin, CreateView):
    model = Tender
    form_class = TenderForm  # ← было fields = [...]
    template_name = 'tenders/tender_form.html'
    success_url = reverse_lazy('tenders:list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        
        # Логируем создание
        self.object._audit_user = self.request.user
        self.object._audit_request = self.request
        from .audit import log_action
        log_action(
            user=self.request.user,
            action='create',
            model_name='Tender',
            object_id=self.object.pk,
            object_repr=str(self.object),
            request=self.request
        )
        
        messages.success(self.request, f'✅ Тендер "{self.object.customer_name}" создан!')
        return response


class TenderUpdateView(LoginRequiredMixin, UpdateView):
    model = Tender
    form_class = TenderForm
    template_name = 'tenders/tender_form.html'
    success_url = reverse_lazy('tenders:list')
    
    def delete(self, request, *args, **kwargs):
        tender = self.get_object()
        messages.success(request, f'🗑️ Тендер "{tender.customer_name}" удалён')
        return super().delete(request, *args, **kwargs)

    def form_valid(self, form):
        if form.instance.client:
            form.instance.customer_name = form.instance.client.name
        
        response = super().form_valid(form)
        
        # Логируем обновление
        from .audit import log_action
        log_action(
            user=self.request.user,
            action='update',
            model_name='Tender',
            object_id=self.object.pk,
            object_repr=str(self.object),
            request=self.request
        )
        
        messages.success(self.request, f'✅ Тендер "{self.object.customer_name}" обновлён!')
        return response
    
class TenderDeleteView(LoginRequiredMixin, DeleteView):
    model = Tender
    template_name = 'tenders/tender_confirm_delete.html'
    success_url = reverse_lazy('tenders:list')
    
    def delete(self, request, *args, **kwargs):
        tender = self.get_object()
        tender._audit_user = request.user
        tender._audit_request = request
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'🗑️ Тендер "{tender.customer_name}" удалён')
        return response

# ============================================
# 🔹 ДАШБОРД
# ============================================
import json
from collections import defaultdict

def dashboard(request):
    """Дашборд со статистикой и графиками"""
    now = timezone.now()
    six_months_ago = now - timedelta(days=180)
    
    # 🔹 БАЗОВАЯ СТАТИСТИКА
    total_tenders = Tender.objects.count()
    won_tenders = Tender.objects.filter(status='won').count()
    active_tenders = Tender.objects.filter(status__in=['submitted', 'published']).count()
    lost_tenders = Tender.objects.filter(status='lost').count()
    draft_tenders = Tender.objects.filter(status='draft').count()
    
    # Конверсия
    conversion = round((won_tenders / total_tenders * 100), 1) if total_tenders > 0 else 0
    
    # 🔹 ФИНАНСЫ
    won_qs = Tender.objects.filter(status='won')
    totals = won_qs.aggregate(
        total_final=Sum('final_amount'),
        total_cost=Sum('cost')
    )
    total_final = totals['total_final'] or 0
    total_cost = totals['total_cost'] or 0
    profit = total_final - total_cost
    
    if total_cost > 0:
        markup_percent = round((profit / total_cost) * 100, 1)
    else:
        markup_percent = 0

    # 🔹 ГРАФИК 1: Статусы тендеров (круговая)
    status_stats = Tender.objects.values('status').annotate(count=Count('id')).order_by('status')
    status_labels = []
    status_data = []
    status_colors = {
        'draft': '#6c757d',
        'submitted': '#0dcaf0',
        'published': '#0d6efd',
        'won': '#198754',
        'lost': '#dc3545',
        'cancelled': '#adb5bd',
    }
    status_display = {
        'draft': 'Черновики',
        'submitted': 'Поданные',
        'published': 'Опубликованные',
        'won': 'Выигранные',
        'lost': 'Проигранные',
        'cancelled': 'Отменённые',
    }
    
    for item in status_stats:
        status = item['status']
        status_labels.append(status_display.get(status, status))
        status_data.append(item['count'])
    
    # 🔹 ГРАФИК 2: Тендеры по месяцам (линейный)
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
    
    monthly_stats = sorted(monthly_data.items())
    month_labels = [m[0] for m in monthly_stats]
    month_totals = [m[1]['total'] for m in monthly_stats]
    month_won = [m[1]['won'] for m in monthly_stats]
    
    # 🔹 ГРАФИК 3: Прибыль по клиентам (столбчатый)
    client_profit = Tender.objects.filter(
        status='won',
        client__isnull=False
    ).values('client__name').annotate(
        profit_sum=Sum(F('final_amount') - F('cost'))
    ).order_by('-profit_sum')[:10]
    
    client_labels = [c['client__name'][:20] for c in client_profit]
    client_data = [float(c['profit_sum'] or 0) for c in client_profit]
    
    # 🔹 Ближайшие дедлайны
    upcoming_deadlines = Tender.objects.filter(
        deadline__gte=now,
    ).order_by('deadline')[:5]
    
    # 🔹 ОТЛАДКА
    print("📊 DEBUG status_labels:", status_labels)
    print("📊 DEBUG status_data:", status_data)
    print("📊 DEBUG month_labels:", month_labels)
    print("📊 DEBUG client_labels:", client_labels)
    
    # 🔹 КОНТЕКСТ
    context = {
    'total_tenders': total_tenders,
    'active_tenders': active_tenders,
    'won_tenders': won_tenders,
    'lost_tenders': lost_tenders,
    'draft_tenders': draft_tenders,
    'win_rate': conversion,
    'total_profit': profit,
    'avg_markup': markup_percent,
    'upcoming_deadlines': upcoming_deadlines,
    
    # Обычные списки (json_script сам их сериализует)
    'status_labels': status_labels,
    'status_data': status_data,
    'status_colors': [status_colors.get(s['status'], '#6c757d') for s in status_stats],
    'month_labels': month_labels,
    'month_totals': month_totals,
    'month_won': month_won,
    'client_labels': client_labels,
    'client_data': client_data,
}
    
    return render(request, 'tenders/dashboard.html', context)

# ============================================
# 🔹 ЭКСПОРТ В EXCEL
# ============================================
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


# ============================================
# 🔹 ПОИСК ТЕНДЕРОВ ОНЛАЙН
# ============================================
class ExternalSearchView(LoginRequiredMixin, View):
    """Поиск тендеров на zakupki.gov.ru"""
    
    def get(self, request):
        form = SearchTenderForm()
        return render(request, 'tenders/external_search.html', {'form': form})
    
    def post(self, request):
        form = SearchTenderForm(request.POST)
        
        if form.is_valid():
            keyword = form.cleaned_data['keyword']
            region = form.cleaned_data['region'] or None
            max_results = form.cleaned_data['max_results']
            
            tenders = search_tenders_on_zakupki(keyword, region, max_results)
        
            return render(request, 'tenders/external_search.html', {
                'form': form,
                'tenders': tenders,
                'search_performed': True,
                'keyword': keyword,
            })
        return render(request, 'tenders/external_search.html', {'form': form})


class ImportTenderView(LoginRequiredMixin, View):
    #Импорт тендера с zakupki.gov.ru в нашу систему"""
    
    def post(self, request):
        try:
            customer_name = request.POST.get('customer_name', 'Не указан')[:200]
            
            # 🔹 АВТОПОИСК клиента по названию заказчика
            client = None
            if customer_name and customer_name != 'Не указан':
                # Ищем точное совпадение или похожее
                client = Client.objects.filter(
                    Q(name__iexact=customer_name) | 
                    Q(name__icontains=customer_name)
                ).first()
            
            tender = Tender(
                customer_name=customer_name,
                client=client,  # ← Привязываем клиента, если найден
                initial_amount=request.POST.get('initial_amount') or 0,
                deadline=request.POST.get('deadline') or None,
                status='draft',
                executor_name='',
                procedure_url=request.POST.get('source_url', ''),
                author=request.user,
                source_url=request.POST.get('source_url', ''),
                external_id=request.POST.get('external_id', ''),
                comment=f"Импортирован с zakupki.gov.ru: {request.POST.get('title', '')}"[:1000],
            )
            tender.save()
            
            if client:
                messages.success(
                    request, 
                    f'✅ Тендер "{customer_name}" импортирован и привязан к клиенту "{client.name}"!'
                )
            else:
                messages.warning(
                    request, 
                    f'⚠️ Тендер "{customer_name}" импортирован. Клиент не найден — '
                    f'<a href="{reverse_lazy("tenders:client_add")}">создайте нового</a>.'
                )
        except Exception as e:
            messages.error(request, f'❌ Ошибка импорта: {e}')
        
        return redirect('tenders:external_search')


# ============================================
# 🔹 CRM: КЛИЕНТЫ
# ============================================
class ClientListView(LoginRequiredMixin, ListView):
    #Список клиентов"""
    model = Client
    template_name = 'tenders/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Client.objects.select_related('manager', 'created_by')
        
        # Фильтрация по поиску
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                db_models.Q(name__icontains=search) |
                db_models.Q(inn__icontains=search) |
                db_models.Q(email__icontains=search) |
                db_models.Q(contact_person__icontains=search)
            )
        
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Фильтрация по менеджеру
        manager = self.request.GET.get('manager')
        if manager:
            queryset = queryset.filter(manager_id=manager)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 🔹 ВАЖНО: в ListView нет self.object!
        context['managers'] = User.objects.filter(is_active=True)
        context['status_choices'] = Client.STATUS_CHOICES
        return context

class ClientCreateView(LoginRequiredMixin, CreateView):
    #Создание клиента"""
    model = Client
    form_class = ClientForm
    template_name = 'tenders/client_form.html'
    success_url = reverse_lazy('tenders:client_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'✅ Клиент "{self.object.name}" успешно добавлен!')
        return response


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    #Редактирование клиента"""
    model = Client
    form_class = ClientForm
    template_name = 'tenders/client_form.html'
    success_url = reverse_lazy('tenders:client_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'✅ Данные клиента "{self.object.name}" обновлены!')
        return response


class ClientDetailView(LoginRequiredMixin, DetailView):
    #Детальная информация о клиенте"""
    model = Client
    template_name = 'tenders/client_detail.html'
    context_object_name = 'client'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 🔹 Здесь self.object — это текущий клиент (правильно!)
        related_tenders = Tender.objects.filter(client=self.object).order_by('-deadline')
        
        # Статистика по клиенту
        total_tenders = related_tenders.count()
        won_tenders = related_tenders.filter(status='won').count()
        total_profit = related_tenders.filter(status='won').aggregate(
            total=Sum(F('final_amount') - F('cost'))
        )['total'] or 0
        
        context['related_tenders'] = related_tenders[:10]
        context['client_stats'] = {
            'total_tenders': total_tenders,
            'won_tenders': won_tenders,
            'win_rate': round(won_tenders / total_tenders * 100, 1) if total_tenders > 0 else 0,
            'total_profit': total_profit,
        }
        
        return context

class ClientDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление клиента"""
    model = Client
    template_name = 'tenders/client_confirm_delete.html'
    success_url = reverse_lazy('tenders:client_list')
    
    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        messages.success(request, f'🗑️ Клиент "{client.name}" удалён')
        return super().delete(request, *args, **kwargs)
    



class TenderDocumentUploadView(LoginRequiredMixin, View):
    """Загрузка документа к тендеру"""
    
    def post(self, request, pk):
        tender = Tender.objects.get(pk=pk)
        
        # Проверка прав доступа
        if tender.author != request.user:
            messages.error(request, '❌ У вас нет прав для добавления документов')
            return redirect('tenders:list')
        
        form = TenderDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.tender = tender
            document.uploaded_by = request.user
            document.save()
            messages.success(request, f'📎 Документ "{document.name}" загружен!')
        else:
            for error in form.errors.values():
                messages.error(request, error)
        
        return redirect('tenders:update', pk=pk)


class TenderDocumentDeleteView(LoginRequiredMixin, View):
    """Удаление документа"""
    
    def post(self, request, pk):
        document = TenderDocument.objects.get(pk=pk)
        
        # Проверка прав доступа
        if document.tender.author != request.user:
            messages.error(request, '❌ У вас нет прав для удаления')
            return redirect('tenders:list')
        
        document_name = document.name
        document.file.delete()  # Удаляем файл с диска
        document.delete()
        messages.success(request, f'🗑️ Документ "{document_name}" удалён')
        
        return redirect('tenders:update', pk=document.tender.pk)
    
   


class AuditLogView(LoginRequiredMixin, ListView):
    """Просмотр лога аудита"""
    model = AuditLog
    template_name = 'tenders/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user')
        
        # Фильтрация по пользователю
        user = self.request.GET.get('user')
        if user:
            queryset = queryset.filter(user_id=user)
        
        # Фильтрация по действию
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Фильтрация по модели
        model_name = self.request.GET.get('model')
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        # Фильтрация по дате
        date_from = self.request.GET.get('date_from')
        if date_from:
            from datetime import datetime
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(timestamp__gte=date_from)
            except:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.filter(is_active=True)
        context['actions'] = AuditLog.ACTION_CHOICES
        context['models'] = ['Tender', 'Client', 'AuditLog']
        return context