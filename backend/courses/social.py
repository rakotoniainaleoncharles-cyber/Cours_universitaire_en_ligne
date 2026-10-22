from .models import SocialPost


def create_admin_activity_post(actor, kind, title, content, *, course=None, subject=None):
    if not actor.is_admin:
        raise ValueError('Seul un administrateur peut publier une activité administrative.')
    return SocialPost.objects.create(
        author=actor,
        kind=kind,
        title=title,
        content=content,
        course=course,
        subject=subject,
    )
