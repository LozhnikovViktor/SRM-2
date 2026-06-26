import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from decimal import Decimal
from django.utils import timezone


def search_tenders_html(keyword, region=None, max_results=20):
    """Поиск актуальных тендеров через HTML zakupki.gov.ru"""
    
    base_url = 'https://zakupki.gov.ru/epz/order/extendedsearch/results.html'
    now = timezone.now()
    
    print(f"\n🔍 HTML ПОИСК: {keyword}")
    print(f"🕐 Текущее время: {now}")
    
    # 🔹 ВАЖНО: фильтруем по дате окончания подачи заявок
    params = {
        'morphology': 'on',
        'searchString': keyword,
        'fz44': 'on',
        'fz223': 'on',
        'sortBy': 'UPDATE_DATE',
        'applicationSubmissionEndDateFrom': now.strftime('%d.%m.%Y'),
        'applicationSubmissionEndDateTo': (now + timedelta(days=180)).strftime('%d.%m.%Y'),
    }
    
    if region:
        params['regionId'] = region
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        print(f"📝 Параметры: {params}")
        
        response = requests.get(base_url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        
        print(f"📊 Статус: {response.status_code}")
        print(f"📦 Размер: {len(response.content)} байт")
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Ищем блоки с тендерами
        tender_blocks = soup.find_all('div', class_='registry-entry__body')
        
        print(f"🔎 Найдено блоков: {len(tender_blocks)}")
        
        tenders = []
        
        for i, block in enumerate(tender_blocks[:max_results], 1):
            try:
                print(f"\n{'='*60}")
                print(f"🔍 БЛОК #{i}")
                
                # Название и ссылка
                title_elem = block.find('a', class_='registry-entry__body-href')
                print(f"📝 title_elem найден: {title_elem is not None}")
                
                if not title_elem:
                    print("❌ Пропуск: нет title_elem")
                    # Попробуем найти любую ссылку
                    any_link = block.find('a')
                    if any_link:
                        print(f"🔗 Найдена другая ссылка: {any_link.get('href', 'N/A')}")
                    continue
                
                title = title_elem.get_text(strip=True)[:500]
                link = title_elem.get('href', '')
                print(f"📄 Название: {title[:80]}")
                print(f"🔗 Ссылка: {link}")
                
                if link and not link.startswith('http'):
                    link = 'https://zakupki.gov.ru' + link
                
                # Номер закупки
                external_id = ''
                number_elem = block.find('div', class_='registry-entry__body-value')
                if number_elem:
                    external_id = number_elem.get_text(strip=True)
                print(f"🆔 Номер: {external_id}")
                
                # Заказчик
                customer_name = ''
                customer_divs = block.find_all('div', class_='registry-entry__body-block')
                for div in customer_divs:
                    if 'Заказчик' in div.get_text():
                        customer_elem = div.find_next('div', class_='registry-entry__body-value')
                        if customer_elem:
                            customer_name = customer_elem.get_text(strip=True)
                            break
                print(f"🏢 Заказчик: {customer_name[:50] if customer_name else 'Не найден'}")
                
                # Сумма
                initial_amount = 0
                price_elem = block.find('div', class_='price-block__value')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    print(f"💰 Цена текст: {price_text}")
                    price_match = re.search(r'([\d\s]+[,.]?\d*)', price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(' ', '').replace(',', '.')
                        try:
                            initial_amount = Decimal(price_str)
                        except:
                            pass
                print(f"💰 Сумма: {initial_amount}")
                
                # Дедлайн
                deadline = None
                deadline_divs = block.find_all('div', class_='registry-entry__body-block')
                for div in deadline_divs:
                    text = div.get_text()
                    if 'Окончание' in text or 'подач' in text.lower():
                        print(f"⏰ Найден блок с дедлайном: {text[:100]}")
                        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
                        if date_match:
                            try:
                                deadline = datetime.strptime(date_match.group(1), '%d.%m.%Y')
                                deadline = timezone.make_aware(deadline, timezone.get_current_timezone())
                                deadline = deadline.replace(hour=23, minute=59, second=59)
                                print(f"✅ Дедлайн: {deadline}")
                                break
                            except Exception as e:
                                print(f"❌ Ошибка парсинга даты: {e}")
                
                # Добавляем тендер
                tenders.append({
                    'title': title,
                    'customer_name': customer_name or 'Не указан',
                    'external_id': external_id,
                    'source_url': link,
                    'description': '',
                    'initial_amount': initial_amount,
                    'deadline': deadline,
                    'pub_date': '',
                })
                print(f"✅ Тендер добавлен!")
                
            except Exception as e:
                print(f"❌ Ошибка парсинга блока: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'='*60}")
        print(f"✅ Актуальных тендеров: {len(tenders)}")
        return tenders
        
    except requests.RequestException as e:
        print(f"❌ Ошибка HTTP: {e}")
        return []
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []