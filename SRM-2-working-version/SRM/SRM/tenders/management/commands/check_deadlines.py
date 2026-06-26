from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from tenders.models import Tender
from datetime import timedelta


class Command(BaseCommand):
    help = 'Проверяет приближающиеся дедлайны тендеров и отправляет уведомления'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=getattr(settings, 'DEADLINE_REMINDER_DAYS', 1),
            help='За сколько дней до дедлайна отправлять уведомления (по умолчанию: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовый запуск без отправки писем'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        now = timezone.now()
        deadline_threshold = now + timedelta(days=days)
        
        self.stdout.write(f'🔍 Проверяем дедлайны на ближайшие {days} дней...')
        self.stdout.write(f'⏰ Текущее время: {now.strftime("%d.%m.%Y %H:%M")}')
        self.stdout.write(f'📅 Порог: {deadline_threshold.strftime("%d.%m.%Y %H:%M")}')
        
        # Находим активные тендеры с приближающимся дедлайном
        urgent_tenders = Tender.objects.filter(
            deadline__gte=now,
            deadline__lte=deadline_threshold,
            status__in=['submitted', 'published', 'draft']
        ).select_related('author', 'client')
        
        if not urgent_tenders.exists():
            self.stdout.write(self.style.SUCCESS('✅ Нет срочных дедлайнов'))
            return
        
        self.stdout.write(self.style.WARNING(f'⚠️ Найдено {urgent_tenders.count()} срочных тендеров'))
        
        # Группируем тендеры по авторам
        tenders_by_user = {}
        for tender in urgent_tenders:
            if tender.author and tender.author.email:
                if tender.author not in tenders_by_user:
                    tenders_by_user[tender.author] = []
                tenders_by_user[tender.author].append(tender)
        
        # Отправляем уведомления каждому пользователю
        sent_count = 0
        for user, user_tenders in tenders_by_user.items():
            if dry_run:
                self.stdout.write(f'📧 [DRY RUN] Письмо для {user.email}: {len(user_tenders)} тендеров')
                for t in user_tenders:
                    self.stdout.write(f'   - {t.customer_name} (дедлайн: {t.deadline.strftime("%d.%m.%Y %H:%M")})')
            else:
                try:
                    self._send_notification(user, user_tenders)
                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✅ Отправлено письмо для {user.email}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Ошибка отправки для {user.email}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Итого отправлено уведомлений: {sent_count}'))
    
    def _send_notification(self, user, tenders):
        """Отправляет email-уведомление пользователю"""
        
        # Формируем список тендеров для письма
        tenders_list = []
        for tender in tenders:
            hours_left = (tender.deadline - timezone.now()).total_seconds() / 3600
            tenders_list.append({
                'customer': tender.customer_name,
                'deadline': tender.deadline.strftime('%d.%m.%Y %H:%M'),
                'hours_left': round(hours_left, 1),
                'amount': tender.initial_amount,
                'status': tender.get_status_display(),
                'url': f'http://127.0.0.1:8000/tenders/{tender.pk}/edit/',
            })
        
        # Тема письма
        subject = f'⚠️ SRM: {len(tenders)} срочных дедлайнов!'
        
        # HTML-версия письма
        html_message = f'''
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #dc3545;">⚠️ Срочные дедлайны тендеров</h2>
            <p>Здравствуйте, <strong>{user.get_full_name() or user.username}</strong>!</p>
            <p>У вас <strong style="color: #dc3545;">{len(tenders)} тендеров</strong> с приближающимся дедлайном:</p>
            
            <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="border: 1px solid #ddd; padding: 10px; text-align: left;">Заказчик</th>
                        <th style="border: 1px solid #ddd; padding: 10px;">Дедлайн</th>
                        <th style="border: 1px solid #ddd; padding: 10px;">Осталось</th>
                        <th style="border: 1px solid #ddd; padding: 10px;">Сумма</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f"""
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 10px;">
                            <a href="{t['url']}">{t['customer']}</a>
                        </td>
                        <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">
                            {t['deadline']}
                        </td>
                        <td style="border: 1px solid #ddd; padding: 10px; text-align: center; color: #dc3545; font-weight: bold;">
                            {t['hours_left']} ч.
                        </td>
                        <td style="border: 1px solid #ddd; padding: 10px; text-align: right;">
                            {t['amount']:,.0f} ₽
                        </td>
                    </tr>
                    """ for t in tenders_list])}
                </tbody>
            </table>
            
            <p style="margin-top: 20px;">
                <a href="http://127.0.0.1:8000/" style="background: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    Открыть SRM
                </a>
            </p>
            
            <hr style="margin-top: 30px;">
            <p style="color: #6c757d; font-size: 12px;">
                Это автоматическое уведомление от системы SRM.<br>
                Настройки уведомлений можно изменить в личном кабинете.
            </p>
        </body>
        </html>
        '''
        
        # Текстовая версия письма
        plain_message = f"Здравствуйте, {user.get_full_name() or user.username}!\n\n"
        plain_message += f"У вас {len(tenders)} срочных тендеров:\n\n"
        for t in tenders_list:
            plain_message += f"• {t['customer']} — дедлайн {t['deadline']} (осталось {t['hours_left']} ч.)\n"
        plain_message += f"\nОткройте SRM: http://127.0.0.1:8000/"
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )