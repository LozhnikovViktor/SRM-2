import xlsxwriter
from io import BytesIO
from django.utils import timezone
from .models import Tender


def export_tenders_to_excel(tenders_qs):
    """Экспорт списка тендеров в Excel"""
    output = BytesIO()
    
    with xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True}) as workbook:
        worksheet = workbook.add_worksheet('Тендеры')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'dd.mm.yyyy'})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        
        # Заголовки
        headers = [
            'ID', 'Заказчик', 'Исполнитель', 'Начальная сумма',
            'Дедлайн', 'Статус', 'Победитель', 'Финальная сумма',
            'Затраты', 'Прибыль'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Данные
        for row, tender in enumerate(tenders_qs, start=1):
            profit = (tender.final_amount - tender.cost) if tender.final_amount and tender.cost else None
            
            worksheet.write(row, 0, tender.id, cell_format)
            worksheet.write(row, 1, tender.customer_name or '', cell_format)
            worksheet.write(row, 2, tender.executor_name or '', cell_format)
            worksheet.write(row, 3, float(tender.initial_amount) if tender.initial_amount else 0, money_format)
            worksheet.write(row, 4, tender.deadline, date_format if tender.deadline else cell_format)
            worksheet.write(row, 5, tender.status, cell_format)
            worksheet.write(row, 6, tender.winner or '', cell_format)
            worksheet.write(row, 7, float(tender.final_amount) if tender.final_amount else 0, money_format)
            worksheet.write(row, 8, float(tender.cost) if tender.cost else 0, money_format)
            worksheet.write(row, 9, profit, money_format if profit else cell_format)
        
        # Автоширина колонок
        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 2, 20)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 12)
        worksheet.set_column(5, 5, 12)
        worksheet.set_column(6, 9, 15)
    
    output.seek(0)
    return output


def export_dashboard_stats_to_excel():
    """Экспорт статистики дашборда в Excel"""
    output = BytesIO()
    
    with xlsxwriter.Workbook(output, {'in_memory': True}) as workbook:
        # Лист 1: Общая статистика
        summary_sheet = workbook.add_worksheet('Общая статистика')
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2196F3',
            'font_color': 'white',
            'border': 1
        })
        
        # Статистика
        total = Tender.objects.count()
        won = Tender.objects.filter(status='won').count()
        active = Tender.objects.filter(status__in=['submitted', 'published']).count()
        
        stats = [
            ['Всего тендеров', total],
            ['Выиграно', won],
            ['Активных', active],
            ['Конверсия', f'{(won/total*100):.1f}%' if total > 0 else '0%'],
        ]
        
        for row, (label, value) in enumerate(stats):
            summary_sheet.write(row, 0, label, header_format)
            summary_sheet.write(row, 1, value, workbook.add_format({'border': 1}))
        
        # Лист 2: По статусам
        status_sheet = workbook.add_worksheet('По статусам')
        
        statuses = Tender.objects.values('status').annotate(count=models.Count('id'))
        
        status_sheet.write(0, 0, 'Статус', header_format)
        status_sheet.write(0, 1, 'Количество', header_format)
        
        for row, item in enumerate(statuses, start=1):
            status_sheet.write(row, 0, item['status'], workbook.add_format({'border': 1}))
            status_sheet.write(row, 1, item['count'], workbook.add_format({'border': 1}))
    
    output.seek(0)
    return output