from flask import Blueprint, render_template

from app.decorators import login_required_student

bp = Blueprint('student', __name__)


@bp.route('/lessons')
@login_required_student
def lessons():
    return render_template('student/lessons.html')
