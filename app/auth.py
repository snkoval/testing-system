from flask import Blueprint, render_template, request, redirect, session, flash

from app import db
from app.models import Teacher, Student
from werkzeug.security import check_password_hash

bp = Blueprint('auth', __name__)


@bp.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        teacher = Teacher.query.filter_by(username=username).first()
        if teacher and check_password_hash(teacher.password_hash, password):
            session['teacher_id'] = teacher.id
            return redirect('/teacher/')

        flash('Неверный логин или пароль', 'error')

    return render_template('auth/teacher_login.html')


@bp.route('/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        login = request.form.get('login', '')
        password = request.form.get('password', '')

        student = Student.query.filter_by(login=login).first()
        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.id
            return redirect('/lessons')

        flash('Неверный логин или пароль', 'error')

    return render_template('auth/student_login.html')


@bp.route('/logout')
def logout():
    is_teacher = 'teacher_id' in session
    is_student = 'student_id' in session
    session.clear()

    if is_teacher:
        return redirect('/admin')
    if is_student:
        return redirect('/login')
    return redirect('/')
