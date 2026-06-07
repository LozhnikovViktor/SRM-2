from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Tender, Client
from .audit import log_model_changes


@receiver(pre_save, sender=Tender)
def tender_pre_save(sender, instance, **kwargs):
    """Сохраняем старые данные тендера перед обновлением"""
    if instance.pk:
        try:
            instance._old_data = Tender.objects.get(pk=instance.pk)
        except Tender.DoesNotExist:
            instance._old_data = None
    else:
        instance._old_data = None


@receiver(post_save, sender=Tender)
def tender_post_save(sender, instance, created, **kwargs):
    """Логируем создание или обновление тендера"""
    if not hasattr(instance, '_audit_user'):
        return
    
    action = 'create' if created else 'update'
    log_model_changes(
        instance=instance,
        action=action,
        user=instance._audit_user,
        request=getattr(instance, '_audit_request', None)
    )


@receiver(post_delete, sender=Tender)
def tender_post_delete(sender, instance, **kwargs):
    """Логируем удаление тендера"""
    if hasattr(instance, '_audit_user'):
        log_model_changes(
            instance=instance,
            action='delete',
            user=instance._audit_user,
            request=getattr(instance, '_audit_request', None)
        )


@receiver(pre_save, sender=Client)
def client_pre_save(sender, instance, **kwargs):
    """Сохраняем старые данные клиента"""
    if instance.pk:
        try:
            instance._old_data = Client.objects.get(pk=instance.pk)
        except Client.DoesNotExist:
            instance._old_data = None
    else:
        instance._old_data = None


@receiver(post_save, sender=Client)
def client_post_save(sender, instance, created, **kwargs):
    """Логируем создание или обновление клиента"""
    if not hasattr(instance, '_audit_user'):
        return
    
    action = 'create' if created else 'update'
    log_model_changes(
        instance=instance,
        action=action,
        user=instance._audit_user,
        request=getattr(instance, '_audit_request', None)
    )


@receiver(post_delete, sender=Client)
def client_post_delete(sender, instance, **kwargs):
    """Логируем удаление клиента"""
    if hasattr(instance, '_audit_user'):
        log_model_changes(
            instance=instance,
            action='delete',
            user=instance._audit_user,
            request=getattr(instance, '_audit_request', None)
        )