from flask import Blueprint, render_template

from app.models import Lesson
from app.decorators import login_required_student
from app.utils import is_lesson_accessible

bp = Blueprint('student', __name__)


@bp.route('/lessons')
@login_required_student
def lessons():
    all_lessons = Lesson.query.order_by(Lesson.order_number.desc()).all()
    accessible = [l for l in all_lessons if is_lesson_accessible(l)]
    return render_template('student/lessons.html', lessons=accessible)
