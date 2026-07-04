import random
import string


PASSWORD_CHARS = string.ascii_lowercase + string.digits + '!@#$%^&*'


def generate_password(length=6):
    return ''.join(random.choice(PASSWORD_CHARS) for _ in range(length))


def generate_login(group_name, seq_number):
    return f'{group_name}_{seq_number}'
