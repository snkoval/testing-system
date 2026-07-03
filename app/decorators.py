from functools import wraps

from flask import session, redirect, flash


def login_required_teacher(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated_function


def login_required_student(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function
