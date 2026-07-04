import random
import string
from datetime import datetime, timezone, timedelta


PASSWORD_CHARS = string.ascii_lowercase + string.digits + '!@#$%^&*'


def generate_password(length=6):
    return ''.join(random.choice(PASSWORD_CHARS) for _ in range(length))


def generate_login(group_name, seq_number):
    return f'{group_name}_{seq_number}'


def is_lesson_accessible(lesson):
    if not lesson.is_open:
        return False
    if lesson.access_days is None:
        return True
    if lesson.opened_at is None:
        return True
    now = datetime.now(timezone.utc)
    opened = lesson.opened_at
    if opened.tzinfo is None:
        opened = opened.replace(tzinfo=timezone.utc)
    expiry = opened + timedelta(days=lesson.access_days)
    return now <= expiry
