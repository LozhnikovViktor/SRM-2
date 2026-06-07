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
from .models import AuditLog
from django.http import JsonResponse
from .forms import CustomUserCreationForm, SearchTenderForm, ClientForm, TenderForm, TenderDocumentForm, TenderFilterForm


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

from .forms import TenderFilterForm


class TenderListView(LoginRequiredMixin, ListView):
    """Расширенный список тендеров с фильтрацией"""
    model = Tender
    template_name = 'tenders/tender_list.html'
    context_object_name = 'tenders'
    paginate_by = 10

    def get_form(self):
        """Создаёт форму с данными из GET-параметров"""
        return TenderFilterForm(self.request.GET)

    def get_queryset(self):
        queryset = Tender.objects.select_related('client', 'author', 'client__manager')
        form = self.get_form()
        
        if not form.is_valid():
            return queryset
        
        data = form.cleaned_data
        
        # 🔹 Текстовый поиск (по нескольким полям сразу)
        if data.get('search'):
            search = data['search']
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(executor_name__icontains=search) |
                Q(winner__icontains=search) |
                Q(comment__icontains=search) |
                Q(client__name__icontains=search) |
                Q(client__inn__icontains=search)
            )
        
        #  Фильтр по статусу (мульти-выбор)
        if data.get('status'):
            queryset = queryset.filter(status__in=data['status'])
        
        # 🔹 Диапазон сумм
        if data.get('amount_from'):
            queryset = queryset.filter(initial_amount__gte=data['amount_from'])
        if data.get('amount_to'):
            queryset = queryset.filter(initial_amount__lte=data['amount_to'])
        
        # 🔹 Диапазон дат дедлайна
        if data.get('deadline_from'):
            queryset = queryset.filter(deadline__date__gte=data['deadline_from'])
        if data.get('deadline_to'):
            queryset = queryset.filter(deadline__date__lte=data['deadline_to'])
        
        # 🔹 Фильтр по клиенту
        if data.get('client'):
            queryset = queryset.filter(client=data['client'])
        
        # 🔹 Фильтр по исполнителю
        if data.get('executor'):
            queryset = queryset.filter(executor_name__icontains=data['executor'])
        
        # 🔹 Быстрые фильтры
        now = timezone.now()
        
        if data.get('urgent_only'):
            queryset = queryset.filter(
                deadline__gte=now,
                deadline__lte=now + timedelta(hours=24),
                status__in=['submitted', 'published', 'draft']
            )
        
        if data.get('overdue_only'):
            queryset = queryset.filter(
                deadline__lt=now,
                status__in=['submitted', 'published', 'draft']
            )
        
        if data.get('has_documents'):
            queryset = queryset.filter(documents__isnull=False).distinct()
        
        # 🔹 Сортировка
        sort = data.get('sort') or '-deadline'
        queryset = queryset.order_by(sort)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.get_form()
        context['total_count'] = self.get_queryset().count()
        
        now = timezone.now()
        context['now'] = now
        
        # Индикаторы срочности
        context['overdue_count'] = Tender.objects.filter(
            deadline__lt=now,
            status__in=['submitted', 'published', 'draft']
        ).count()
        
        context['urgent_count'] = Tender.objects.filter(
            deadline__gte=now,
            deadline__lte=now + timedelta(hours=24),
            status__in=['submitted', 'published', 'draft']
        ).count()
        
        # Активные фильтры для отображения бейджей
        context['active_filters'] = self._get_active_filters()
        
        return context
    
    def _get_active_filters(self):
        """Возвращает список активных фильтров для отображения"""
        form = self.get_form()
        if not form.is_valid():
            return []
        
        data = form.cleaned_data
        filters = []
        
        if data.get('search'):
            filters.append({'name': 'Поиск', 'value': data['search'], 'param': 'search'})
        
        if data.get('status'):
            status_labels = dict(TenderFilterForm.base_fields['status'].choices)
            for s in data['status']:
                filters.append({'name': 'Статус', 'value': status_labels.get(s, s), 'param': 'status', 'value_param': s})
        
        if data.get('amount_from'):
            filters.append({'name': 'Сумма от', 'value': f'{data["amount_from"]:,.0f} ₽', 'param': 'amount_from'})
        if data.get('amount_to'):
            filters.append({'name': 'Сумма до', 'value': f'{data["amount_to"]:,.0f} ₽', 'param': 'amount_to'})
        
        if data.get('deadline_from'):
            filters.append({'name': 'Дедлайн от', 'value': data['deadline_from'].strftime('%d.%m.%Y'), 'param': 'deadline_from'})
        if data.get('deadline_to'):
            filters.append({'name': 'Дедлайн до', 'value': data['deadline_to'].strftime('%d.%m.%Y'), 'param': 'deadline_to'})
        
        if data.get('client'):
            filters.append({'name': 'Клиент', 'value': str(data['client']), 'param': 'client'})
        
        if data.get('executor'):
            filters.append({'name': 'Исполнитель', 'value': data['executor'], 'param': 'executor'})
        
        if data.get('urgent_only'):
            filters.append({'name': 'Срочные', 'value': '24 часа', 'param': 'urgent_only'})
        
        if data.get('overdue_only'):
            filters.append({'name': 'Просроченные', 'value': '', 'param': 'overdue_only'})
        
        if data.get('has_documents'):
            filters.append({'name': 'С документами', 'value': '', 'param': 'has_documents'})
        
        return filters

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
    
    # 🔹 ВОРОНКА ПРОДАЖ
    funnel_data = {
        'draft': Tender.objects.filter(status='draft').count(),
        'submitted': Tender.objects.filter(status__in=['submitted', 'published']).count(),
        'won': Tender.objects.filter(status='won').count(),
    }
    
    funnel_conversion = {}
    if funnel_data['draft'] > 0:
        funnel_conversion['draft_to_submitted'] = round(
            (funnel_data['submitted'] / funnel_data['draft']) * 100, 1
        )
    else:
        funnel_conversion['draft_to_submitted'] = 0
    
    if funnel_data['submitted'] > 0:
        funnel_conversion['submitted_to_won'] = round(
            (funnel_data['won'] / funnel_data['submitted']) * 100, 1
        )
    else:
        funnel_conversion['submitted_to_won'] = 0
    
    # 🔹 Ближайшие дедлайны
    upcoming_deadlines = Tender.objects.filter(
        deadline__gte=now,
    ).order_by('deadline')[:5]
    
    # 🔹 ОТЛАДКА
    print("📊 DEBUG status_labels:", status_labels)
    print("📊 DEBUG status_data:", status_data)
    print("📊 DEBUG month_labels:", month_labels)
    print("📊 DEBUG client_labels:", client_labels)
    print("📊 DEBUG funnel_data:", funnel_data)
    
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
        
        # Данные для графиков - как JSON строки
        'status_labels_json': json.dumps(status_labels, ensure_ascii=False),
        'status_data_json': json.dumps(status_data),
        'status_colors_json': json.dumps([status_colors.get(s['status'], '#6c757d') for s in status_stats]),
        'month_labels_json': json.dumps(month_labels),
        'month_totals_json': json.dumps(month_totals),
        'month_won_json': json.dumps(month_won),
        'client_labels_json': json.dumps(client_labels, ensure_ascii=False),
        'client_data_json': json.dumps(client_data),
        
        # Воронка продаж
        'funnel_data': funnel_data,
        'funnel_conversion': funnel_conversion,
        'funnel_data_json': json.dumps(funnel_data),
    }
    
    return render(request, 'tenders/dashboard.html', context)


    
        # 🔹 ДАННЫЕ ДЛЯ ВОРОНКИ ПРОДАЖ
    funnel_data = {
        'draft': Tender.objects.filter(status='draft').count(),
        'submitted': Tender.objects.filter(status__in=['submitted', 'published']).count(),
        'won': Tender.objects.filter(status='won').count(),
    }

    # Рассчитываем конверсию между этапами
    funnel_conversion = {}
    if funnel_data['draft'] > 0:
        funnel_conversion['draft_to_submitted'] = round(
            (funnel_data['submitted'] / funnel_data['draft']) * 100, 1
        )
    else:
        funnel_conversion['draft_to_submitted'] = 0
    
    if funnel_data['submitted'] > 0:
        funnel_conversion['submitted_to_won'] = round(
            (funnel_data['won'] / funnel_data['submitted']) * 100, 1
        )
    else:
        funnel_conversion['submitted_to_won'] = 0
    
    # Добавляем в контекст
    context['funnel_data'] = funnel_data
    context['funnel_conversion'] = funnel_conversion
    context['funnel_data_json'] = json.dumps(funnel_data)  # ← ДОБАВЬТЕ ЭТУ СТРОКУ!

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
        context['now'] = timezone.now() 
        
        # 🔹 Индикаторы срочности
        now = timezone.now()
        
        # Количество просроченных тендеров
        context['overdue_count'] = Tender.objects.filter(
            deadline__lt=now,
            status__in=['submitted', 'published', 'draft']
        ).count()
        
        # Количество срочных (в ближайшие 24 часа)
        context['urgent_count'] = Tender.objects.filter(
            deadline__gte=now,
            deadline__lte=now + timedelta(hours=24),
            status__in=['submitted', 'published', 'draft']
        ).count()
        
        # Количество с дедлайном в ближайшие 3 дня
        context['upcoming_count'] = Tender.objects.filter(
            deadline__gte=now,
            deadline__lte=now + timedelta(days=3),
            status__in=['submitted', 'published', 'draft']
        ).count()
        
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
        context['now'] = timezone.now()
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
    
class TenderKanbanView(LoginRequiredMixin, View):
    """Канбан-доска для визуального управления тендерами"""
    template_name = 'tenders/kanban.html'
    
    def get(self, request):
        tenders = Tender.objects.all().order_by('-deadline')
        
        # Группируем тендеры по статусам
        context = {
            'draft': tenders.filter(status='draft'),
            'process': tenders.filter(status__in=['submitted', 'published']),
            'won': tenders.filter(status='won'),
            'lost': tenders.filter(status__in=['lost', 'cancelled']),
        }
        
        return render(request, self.template_name, context)


class TenderStatusUpdateView(LoginRequiredMixin, View):
    """API endpoint для обновления статуса через Drag&Drop"""
    
    def post(self, request):
        try:
            import json
            data = json.loads(request.body)
            tender_id = data.get('tender_id')
            new_status = data.get('status')
            
            if not tender_id or not new_status:
                return HttpResponse(json.dumps({'status': 'error', 'message': 'Missing data'}), content_type='application/json', status=400)
            
            tender = Tender.objects.get(pk=tender_id)
            old_status = tender.status
            tender.status = new_status
            tender.save()
            
            # 🔹 Логирование изменения
            from .audit import log_action
            log_action(
                user=request.user,
                action='update',
                model_name='Tender',
                object_id=tender.pk,
                object_repr=str(tender),
                changes={'status': {'old': old_status, 'new': new_status}},
                request=request
            )
            
            return HttpResponse(json.dumps({'status': 'success'}), content_type='application/json')
            
        except Tender.DoesNotExist:
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Tender not found'}), content_type='application/json', status=404)
        except Exception as e:
            return HttpResponse(json.dumps({'status': 'error', 'message': str(e)}), content_type='application/json', status=500)
        



class TenderCalendarView(LoginRequiredMixin, View):
    """Интерактивный календарь дедлайнов"""
    template_name = 'tenders/calendar.html'
    
    def get(self, request):
        return render(request, self.template_name)


class TenderCalendarDataView(LoginRequiredMixin, View):
    """API endpoint для получения данных календаря"""
    
    def get(self, request):
        # Получаем параметры фильтрации
        start = request.GET.get('start')
        end = request.GET.get('end')
        
        tenders = Tender.objects.filter(deadline__isnull=False)
        
        # Фильтрация по исполнителю
        executor = request.GET.get('executor')
        if executor:
            tenders = tenders.filter(executor_name__icontains=executor)
        
        # Фильтрация по статусу
        status = request.GET.get('status')
        if status:
            tenders = tenders.filter(status=status)
        
        # Формируем данные для календаря
        events = []
        for tender in tenders:
            # Цвет в зависимости от статуса
            color_map = {
                'draft': '#6c757d',      # серый
                'submitted': '#0dcaf0',  # голубой
                'published': '#0d6efd',  # синий
                'won': '#198754',        # зелёный
                'lost': '#dc3545',       # красный
                'cancelled': '#adb5bd',  # светло-серый
            }
            
            color = color_map.get(tender.status, '#6c757d')
            
            events.append({
                'id': tender.pk,
                'title': f"{tender.customer_name[:30]} ({tender.initial_amount:,.0f}₽)",
                'start': tender.deadline.isoformat(),
                'url': f"/tenders/{tender.pk}/edit/",
                'color': color,
                'extendedProps': {
                    'status': tender.get_status_display(),
                    'amount': tender.initial_amount,
                    'executor': tender.executor_name or 'Не указан'
                }
            })
        
        return JsonResponse(events, safe=False)