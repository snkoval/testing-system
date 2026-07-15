import json

from flask import Blueprint, render_template, abort, redirect, request, jsonify, session

from app import db
from app.models import Lesson, Task, Student, Submission, GroupSection
from app.decorators import login_required_student
from app.utils import is_lesson_accessible
from app.test_files import get_examples
from app.checker import check_submission

bp = Blueprint('student', __name__)


def _get_student_section_ids(student):
    links = GroupSection.query.filter_by(group_id=student.group_id).all()
    return [link.section_id for link in links]


@bp.route('/lessons')
@login_required_student
def lessons():
    student = db.session.get(Student, session['student_id'])
    section_ids = _get_student_section_ids(student)
    if section_ids:
        all_lessons = Lesson.query \
            .filter(Lesson.section_id.in_(section_ids)) \
            .order_by(Lesson.order_number.desc()).all()
    else:
        all_lessons = Lesson.query \
            .order_by(Lesson.order_number.desc()).all()
    accessible = [l for l in all_lessons if is_lesson_accessible(l)]

    sections = {}
    for l in accessible:
        sname = l.section.name if l.section else 'Уроки'
        if sname not in sections:
            sections[sname] = []
        sections[sname].append(l)

    return render_template('student/lessons.html', sections=sections)


@bp.route('/lessons/<int:lesson_id>')
@login_required_student
def lesson(lesson_id):
    student = db.session.get(Student, session['student_id'])
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        abort(404)

    section_ids = _get_student_section_ids(student)
    if section_ids and lesson.section_id not in section_ids:
        abort(403)

    if not is_lesson_accessible(lesson):
        return redirect('/lessons')
    tasks = Task.query.filter_by(lesson_id=lesson_id) \
        .order_by(Task.letter_index).all()
    first_task = tasks[0] if tasks else None
    examples = get_examples(first_task.id, first_task.show_examples) if first_task else []

    submission = None
    if first_task:
        submission = Submission.query.filter_by(
            student_id=session['student_id'], task_id=first_task.id
        ).first()

    return render_template('student/lesson.html', lesson=lesson,
                           tasks=tasks, first_task=first_task,
                           task=first_task, examples=examples,
                           submission=submission,
                           allowed_languages=lesson.allowed_languages or 'python,cpp')


@bp.route('/lessons/<int:lesson_id>/tasks/<int:task_id>')
@login_required_student
def task_statement(lesson_id, task_id):
    student = db.session.get(Student, session['student_id'])
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        abort(404)

    section_ids = _get_student_section_ids(student)
    if section_ids and lesson.section_id not in section_ids:
        abort(403)

    if not is_lesson_accessible(lesson):
        abort(404)
    task = db.session.get(Task, task_id)
    if task is None or task.lesson_id != lesson_id:
        abort(404)
    examples = get_examples(task_id, task.show_examples)

    submission = Submission.query.filter_by(
        student_id=session['student_id'], task_id=task_id
    ).first()

    return render_template('student/task_statement.html', task=task,
                           examples=examples, submission=submission)


@bp.route('/submit', methods=['POST'])
@login_required_student
def submit():
    task_id = request.form.get('task_id')
    if not task_id:
        abort(404)

    task = db.session.get(Task, int(task_id))
    if task is None:
        abort(404)

    lesson = db.session.get(Lesson, task.lesson_id)
    if lesson is None or not is_lesson_accessible(lesson):
        abort(403)

    code = request.form.get('code')
    language = request.form.get('language')

    if not code:
        return jsonify({'error': 'Код не может быть пустым'}), 400

    result = check_submission(code, language, task_id)

    student_id = session['student_id']
    submission = Submission.query.filter_by(
        student_id=student_id, task_id=task_id
    ).first()

    if submission:
        submission.code = code
        submission.language = language
        submission.test_results = json.dumps(result)
    else:
        submission = Submission(
            student_id=student_id,
            task_id=task_id,
            code=code,
            language=language,
            test_results=json.dumps(result),
        )
        db.session.add(submission)

    db.session.commit()
    return jsonify(result)
