import xlsxwriter
from io import BytesIO
from django.utils import timezone
from .models import Tender
from django.db import models  # ← ДОБАВЬТЕ ЭТУ СТРОК
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime
import time
from decimal import Decimal


def search_tenders_on_zakupki(keyword, region=None, max_results=20):
    """
    Поиск тендеров на zakupki.gov.ru через RSS-ленту
    
    Args:
        keyword: Ключевое слово для поиска
        region: Код региона (необязательно)
        max_results: Максимальное количество результатов
    
    Returns:
        Список словарей с данными тендеров
    """
    # Формируем URL для RSS-поиска
    base_url = 'https://zakupki.gov.ru/epz/order/extendedsearch/rss.html'
    
    params = {
        'morphology': 'on',
        'searchString': keyword,
        'fz44': 'on',       # Федеральный закон 44-ФЗ (государственные закупки)
        'fz223': 'on',      # Федеральный закон 223-ФЗ (закупки госкомпаний)
        'sortBy': 'UPDATE_DATE',
        'showLotsInfoHidden': 'false',
    }
    
    if region:
        params['regionId'] = region
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml,application/xml,text/xml'
        }
        
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Парсим RSS-ленту
        root = ET.fromstring(response.content)
        tenders = []
        
        # Namespace для RSS
        namespaces = {
            'ns0': 'http://zakupki.gov.ru/223fz/lot/1',
            'ns1': 'http://zakupki.gov.ru/223fz/dishonestSupplier/1',
        }
        
        for item in root.findall('.//item')[:max_results]:
            try:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                description = item.find('description').text if item.find('description') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                
                # Извлекаем ID из ссылки (например, 0123456789)
                external_id = link.split('/')[-1] if '/' in link else ''
                
                # Парсим описание для извлечения суммы
                initial_amount = 0
                customer_name = ''
                deadline = None
                
                # Пытаемся извлечь информацию из HTML описания
                soup = BeautifulSoup(description, 'lxml')
                text_desc = soup.get_text()
                
                # Ищем сумму (например, "1 234 567,89 руб")
                import re
                price_match = re.search(r'([\d\s]+[,.]?\d*)\s*(?:руб|₽)', text_desc)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace(',', '.')
                    try:
                        initial_amount = Decimal(price_str)
                    except:
                        initial_amount = 0
                
                # Ищем заказчика
                customer_match = re.search(r'Заказчик[:\s]+([^\n,]+)', text_desc)
                if customer_match:
                    customer_name = customer_match.group(1).strip()
                
                # Пытаемся распарсить дату публикации
                try:
                    # Формат: "Mon, 03 Jun 2026 10:00:00 +0300"
                    from email.utils import parsedate_to_datetime
                    deadline = parsedate_to_datetime(pub_date)
                except:
                    deadline = None
                
                tenders.append({
                    'title': title[:500] if title else 'Без названия',
                    'customer_name': customer_name[:200] if customer_name else 'Не указан',
                    'external_id': external_id,
                    'source_url': link,
                    'description': text_desc[:1000],
                    'initial_amount': initial_amount,
                    'deadline': deadline,
                    'pub_date': pub_date,
                })
                
            except Exception as e:
                print(f"Ошибка парсинга элемента: {e}")
                continue
        
        return tenders
        
    except requests.RequestException as e:
        print(f"Ошибка HTTP запроса: {e}")
        return []
    except ET.ParseError as e:
        print(f"Ошибка парсинга XML: {e}")
        return []
    
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
            'Затраты', 'Прибыль', 'Комментарий'
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
            worksheet.write(row, 10, tender.comment or '', cell_format)  # ← добавили
        
        # Автоширина колонок
        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 2, 20)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 12)
        worksheet.set_column(5, 5, 12)
        worksheet.set_column(6, 9, 15)
        worksheet.set_column(10, 10, 30)  # ← добавили (ширина для комментария)
    
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