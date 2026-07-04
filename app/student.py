from flask import Blueprint, render_template, abort, redirect

from app import db
from app.models import Lesson, Task
from app.decorators import login_required_student
from app.utils import is_lesson_accessible
from app.test_files import get_examples

bp = Blueprint('student', __name__)


@bp.route('/lessons')
@login_required_student
def lessons():
    all_lessons = Lesson.query.order_by(Lesson.order_number.desc()).all()
    accessible = [l for l in all_lessons if is_lesson_accessible(l)]
    return render_template('student/lessons.html', lessons=accessible)


@bp.route('/lessons/<int:lesson_id>')
@login_required_student
def lesson(lesson_id):
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        abort(404)
    if not is_lesson_accessible(lesson):
        return redirect('/lessons')
    tasks = Task.query.filter_by(lesson_id=lesson_id) \
        .order_by(Task.letter_index).all()
    first_task = tasks[0] if tasks else None
    examples = get_examples(first_task.id) if first_task else []
    return render_template('student/lesson.html', lesson=lesson,
                           tasks=tasks, first_task=first_task,
                           task=first_task, examples=examples)


@bp.route('/lessons/<int:lesson_id>/tasks/<int:task_id>')
@login_required_student
def task_statement(lesson_id, task_id):
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        abort(404)
    if not is_lesson_accessible(lesson):
        abort(404)
    task = db.session.get(Task, task_id)
    if task is None or task.lesson_id != lesson_id:
        abort(404)
    examples = get_examples(task_id)
    return render_template('student/task_statement.html', task=task,
                           examples=examples)
