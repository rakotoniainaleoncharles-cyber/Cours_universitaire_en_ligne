from .models import AdminAuditLog


def log_admin_action(actor, action, resource_type, resource_id, description):
    AdminAuditLog.objects.create(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id or ''),
        description=description[:255],
    )
