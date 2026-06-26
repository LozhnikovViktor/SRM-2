from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from tenders.models import Tender


class Command(BaseCommand):
    help = 'Отправляет email-уведомления о приближающихся дедлайнах'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='За сколько дней до дедлайна отправлять уведомление',
        )

    def handle(self, *args, **kwargs):
        days = kwargs['days']
        now = timezone.now()
        deadline_limit = now + timedelta(days=days)

        upcoming_tenders = Tender.objects.filter(
            deadline__gte=now,
            deadline__lte=deadline_limit,
            status__in=['submitted', 'published', 'draft']
        ).select_related('author')

        if not upcoming_tenders:
            self.stdout.write(self.style.WARNING('Нет тендеров с приближающимися дедлайнами.'))
            return

        self.stdout.write(f'Найдено тендеров: {upcoming_tenders.count()}')

        for tender in upcoming_tenders:
            recipient = tender.author.email
            
            if not recipient:
                self.stdout.write(self.style.WARNING(f'Пользователь {tender.author.username} без email'))
                continue

            subject = f'⏰ Дедлайн тендера "{tender.customer_name}"'
            message = (
                f'Здравствуйте, {tender.author.username}!\n\n'
                f'Напоминаем: дедлайн тендера "{tender.customer_name}" '
                f'истекает {tender.deadline.strftime("%d.%m.%Y в %H:%M")}.\n\n'
                f'Система SRM Тендеры'
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Отправлено на {recipient}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Ошибка: {e}'))