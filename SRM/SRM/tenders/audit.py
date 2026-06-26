import json
from .models import AuditLog


def log_action(user, action, model_name, object_id=None, object_repr='', changes=None, request=None):
    """
    Записать действие в лог аудита
    """
    ip_address = None
    user_agent = None
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    changes_json = None
    if changes:
        try:
            changes_json = json.dumps(changes, ensure_ascii=False, default=str)
        except:
            changes_json = str(changes)
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr[:200] if object_repr else '',
        changes=changes_json,
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_model_changes(instance, action, user, request=None):
    """
    Автоматически логировать изменения модели
    """
    model_name = instance.__class__.__name__
    object_id = instance.pk
    object_repr = str(instance)[:200]
    
    changes = None
    if action == 'update' and hasattr(instance, '_old_data'):
        old_data = instance._old_data
        new_data = {}
        
        for field in instance._meta.fields:
            field_name = field.name
            old_value = getattr(old_data, field_name, None) if old_data else None
            new_value = getattr(instance, field_name, None)
            
            if old_value != new_value:
                new_data[field_name] = {
                    'old': str(old_value),
                    'new': str(new_value)
                }
        
        if new_data:
            changes = new_data
    
    log_action(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes,
        request=request
    )