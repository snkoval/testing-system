import os
import tempfile

import pytest

from app import db
from app.models import Teacher, Group, Student, Lesson, Task, Submission


class TestTeacher:
    def test_create_teacher(self, app):
        with app.app_context():
            t = Teacher(username='admin', password_hash='hash123')
            db.session.add(t)
            db.session.commit()
            assert t.id is not None
            assert t.username == 'admin'

    def test_username_unique(self, app):
        with app.app_context():
            t1 = Teacher(username='admin', password_hash='h1')
            db.session.add(t1)
            db.session.commit()
            t2 = Teacher(username='admin', password_hash='h2')
            db.session.add(t2)
            with pytest.raises(Exception):
                db.session.commit()


class TestGroup:
    def test_create_group(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            assert g.id is not None
            assert g.name == '7A_1gr'

    def test_group_has_students_relation(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            assert hasattr(g, 'students')
            assert g.students == []


class TestStudent:
    def test_create_student(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id,
                login='7A_1gr_1',
                password_hash='hash',
                password_plain='abc123',
                last_name='Иванов',
                first_name='Иван',
                seq_number=1
            )
            db.session.add(s)
            db.session.commit()
            assert s.id is not None
            assert s.login == '7A_1gr_1'
            assert s.last_name == 'Иванов'
            assert s.first_name == 'Иван'
            assert s.seq_number == 1

    def test_login_unique(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s1 = Student(group_id=g.id, login='7A_1gr_1', password_hash='h',
                         password_plain='abc123',
                         last_name='А', first_name='А', seq_number=1)
            s2 = Student(group_id=g.id, login='7A_1gr_1', password_hash='h',
                         password_plain='def456',
                         last_name='Б', first_name='Б', seq_number=2)
            db.session.add_all([s1, s2])
            with pytest.raises(Exception):
                db.session.commit()

    def test_student_group_relationship(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(group_id=g.id, login='7A_1gr_1', password_hash='h',
                        password_plain='abc',
                        last_name='И', first_name='И', seq_number=1)
            db.session.add(s)
            db.session.commit()
            assert s.group == g
            assert s in g.students


class TestLesson:
    def test_create_lesson(self, app):
        with app.app_context():
            l = Lesson(order_number=1, title='Ввод и вывод')
            db.session.add(l)
            db.session.commit()
            assert l.id is not None
            assert l.order_number == 1
            assert l.title == 'Ввод и вывод'

    def test_lesson_defaults(self, app):
        with app.app_context():
            l = Lesson(order_number=1, title='Тест')
            db.session.add(l)
            db.session.commit()
            assert l.is_open is False
            assert l.access_days is None
            assert l.opened_at is None
            assert l.theory_url is None

    def test_lesson_with_theory_url(self, app):
        with app.app_context():
            l = Lesson(order_number=2, title='Циклы', theory_url='https://example.com')
            db.session.add(l)
            db.session.commit()
            assert l.theory_url == 'https://example.com'

    def test_lesson_has_tasks_relation(self, app):
        with app.app_context():
            l = Lesson(order_number=1, title='Тест')
            db.session.add(l)
            db.session.commit()
            assert hasattr(l, 'tasks')
            assert l.tasks == []


class TestTask:
    def test_create_task(self, app):
        with app.app_context():
            l = Lesson(order_number=1, title='Урок')
            db.session.add(l)
            db.session.commit()
            t = Task(
                lesson_id=l.id,
                letter_index='A',
                short_title='Hello World',
                problem_text='Выведите Hello World',
                input_description='Нет ввода',
                output_description='Hello World'
            )
            db.session.add(t)
            db.session.commit()
            assert t.id is not None
            assert t.letter_index == 'A'
            assert t.short_title == 'Hello World'

    def test_task_defaults(self, app):
        with app.app_context():
            l = Lesson(order_number=1, title='Урок')
            db.session.add(l)
            db.session.commit()
            t = Task(
                lesson_id=l.id,
                letter_index='A',
                short_title='Test',
                problem_text='Text',
                input_description='In',
                output_description='Out'
            )
            db.session.add(t)
            db.session.commit()
            assert t.time_limit == 1
            assert t.memory_limit == 256
            assert t.notes is None

    def test_task_lesson_relationship(self, app):
        with app.app_context():
            l = Lesson(order_number=1, title='Урок')
            db.session.add(l)
            db.session.commit()
            t = Task(
                lesson_id=l.id, letter_index='A', short_title='T',
                problem_text='P', input_description='I', output_description='O'
            )
            db.session.add(t)
            db.session.commit()
            assert t.lesson == l
            assert t in l.tasks


class TestSubmission:
    def test_create_submission(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            l = Lesson(order_number=1, title='Урок')
            db.session.add(l)
            db.session.commit()
            s = Student(group_id=g.id, login='7A_1gr_1', password_hash='h',
                        password_plain='abc',
                        last_name='И', first_name='И', seq_number=1)
            db.session.add(s)
            t = Task(lesson_id=l.id, letter_index='A', short_title='T',
                     problem_text='P', input_description='I', output_description='O')
            db.session.add(t)
            db.session.commit()
            sub = Submission(
                student_id=s.id, task_id=t.id,
                code='print("hello")', language='python',
                test_results='{"passed": 2, "total": 2}'
            )
            db.session.add(sub)
            db.session.commit()
            assert sub.id is not None
            assert sub.code == 'print("hello")'
            assert sub.language == 'python'

    def test_submission_datetime(self, app):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            l = Lesson(order_number=1, title='Урок')
            db.session.add(l)
            db.session.commit()
            s = Student(group_id=g.id, login='7A_1gr_1', password_hash='h',
                        password_plain='abc',
                        last_name='И', first_name='И', seq_number=1)
            db.session.add(s)
            t = Task(lesson_id=l.id, letter_index='A', short_title='T',
                     problem_text='P', input_description='I', output_description='O')
            db.session.add(t)
            db.session.commit()
            sub = Submission(
                student_id=s.id, task_id=t.id,
                code='x=1', language='cpp', test_results='{}'
            )
            db.session.add(sub)
            db.session.commit()
            assert sub.submitted_at is not None
