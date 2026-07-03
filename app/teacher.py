from flask import Blueprint, render_template, request, redirect, session, flash

from app import db
from app.models import Teacher
from app.decorators import login_required_teacher
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint('teacher', __name__, url_prefix='/teacher')


@bp.route('/')
@login_required_teacher
def index():
    return render_template('teacher/dashboard.html')


@bp.route('/groups')
@login_required_teacher
def groups():
    return render_template('teacher/groups.html')


@bp.route('/settings', methods=['GET', 'POST'])
@login_required_teacher
def settings():
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        teacher = db.session.get(Teacher, session['teacher_id'])

        if not check_password_hash(teacher.password_hash, old_password):
            flash('Неверный старый пароль', 'error')
            return render_template('teacher/settings.html')

        if new_password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('teacher/settings.html')

        teacher.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Пароль успешно изменён', 'success')
        return redirect('/teacher/settings')

    return render_template('teacher/settings.html')
