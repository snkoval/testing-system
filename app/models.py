from datetime import datetime, timezone

from app import db


class Teacher(db.Model):
    __tablename__ = 'teacher'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


class Group(db.Model):
    __tablename__ = 'group'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    students = db.relationship('Student', backref='group', lazy=True,
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Group {self.name}>'


class Student(db.Model):
    __tablename__ = 'student'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    password_plain = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    seq_number = db.Column(db.Integer, nullable=False)

    submissions = db.relationship('Submission', backref='student', lazy=True,
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Student {self.login}>'


class Section(db.Model):
    __tablename__ = 'section'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    order_number = db.Column(db.Integer, nullable=False)

    lessons = db.relationship('Lesson', backref='section', lazy=True)
    group_links = db.relationship('GroupSection', backref='section',
                                   lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Section {self.order_number}: {self.name}>'


class GroupSection(db.Model):
    __tablename__ = 'group_section'

    group_id = db.Column(db.Integer, db.ForeignKey('group.id'),
                         primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'),
                           primary_key=True)


class Lesson(db.Model):
    __tablename__ = 'lesson'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'),
                           nullable=True)
    order_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    theory_url = db.Column(db.String(500), nullable=True)
    is_open = db.Column(db.Boolean, nullable=False, default=False)
    access_days = db.Column(db.Integer, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=True)
    allowed_languages = db.Column(db.String(20), nullable=False,
                                  default='python,cpp')

    tasks = db.relationship('Task', backref='lesson', lazy=True,
                            cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Lesson {self.order_number}: {self.title}>'


class Task(db.Model):
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    letter_index = db.Column(db.String(1), nullable=False)
    short_title = db.Column(db.String(200), nullable=False)
    problem_text = db.Column(db.Text, nullable=False)
    input_description = db.Column(db.Text, nullable=False)
    output_description = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    time_limit = db.Column(db.Integer, nullable=False, default=1)
    memory_limit = db.Column(db.Integer, nullable=False, default=256)
    show_examples = db.Column(db.Integer, nullable=False, default=2)

    submissions = db.relationship('Submission', backref='task', lazy=True,
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Task {self.letter_index}: {self.short_title}>'


class Submission(db.Model):
    __tablename__ = 'submission'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'task_id', name='uq_student_task'),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False)
    test_results = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Submission {self.student_id}->{self.task_id}>'
