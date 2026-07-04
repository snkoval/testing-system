from datetime import datetime, timezone, timedelta

import pytest

from app import db
from app.models import Teacher, Group, Student, Lesson
from app.utils import is_lesson_accessible
from werkzeug.security import generate_password_hash


@pytest.fixture
def teacher(app):
    with app.app_context():
        t = Teacher(username='admin', password_hash=generate_password_hash('secret123'))
        db.session.add(t)
        db.session.commit()
        return t


@pytest.fixture
def logged_in_client(client, teacher):
    client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
    return client


class TestIsLessonAccessible:
    def test_closed_lesson_not_accessible(self):
        lesson = Lesson(order_number=1, title='Test', is_open=False)
        assert not is_lesson_accessible(lesson)

    def test_open_no_expiry_accessible(self):
        lesson = Lesson(
            order_number=1, title='Test', is_open=True,
            access_days=None,
            opened_at=datetime.now(timezone.utc)
        )
        assert is_lesson_accessible(lesson)

    def test_open_within_period(self):
        lesson = Lesson(
            order_number=1, title='Test', is_open=True,
            access_days=7,
            opened_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        assert is_lesson_accessible(lesson)

    def test_open_expired(self):
        lesson = Lesson(
            order_number=1, title='Test', is_open=True,
            access_days=2,
            opened_at=datetime.now(timezone.utc) - timedelta(days=5)
        )
        assert not is_lesson_accessible(lesson)

    def test_open_expired_exact_boundary(self):
        lesson = Lesson(
            order_number=1, title='Test', is_open=True,
            access_days=3,
            opened_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        assert is_lesson_accessible(lesson)


class TestLessonList:
    def test_get_lessons_page(self, logged_in_client):
        response = logged_in_client.get('/teacher/lessons')
        assert response.status_code == 200

    def test_lessons_page_shows_lesson(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Переменные')
            db.session.add(l)
            db.session.commit()
        response = logged_in_client.get('/teacher/lessons')
        assert b'\xd0\x9f\xd0\xb5\xd1\x80\xd0\xb5\xd0\xbc\xd0\xb5\xd0\xbd\xd0\xbd\xd1\x8b\xd0\xb5' in response.data


class TestCreateLesson:
    def test_get_create_form(self, logged_in_client):
        response = logged_in_client.get('/teacher/lessons/create')
        assert response.status_code == 200

    def test_create_lesson(self, app, logged_in_client):
        response = logged_in_client.post('/teacher/lessons/create', data={
            'order_number': '1',
            'title': 'Введение в Python',
            'theory_url': 'https://example.com/python'
        })
        assert response.status_code == 302
        with app.app_context():
            l = Lesson.query.filter_by(title='Введение в Python').first()
            assert l is not None
            assert l.order_number == 1
            assert l.theory_url == 'https://example.com/python'

    def test_create_without_theory_url(self, app, logged_in_client):
        response = logged_in_client.post('/teacher/lessons/create', data={
            'order_number': '2',
            'title': 'Условия',
            'theory_url': ''
        })
        assert response.status_code == 302
        with app.app_context():
            l = Lesson.query.filter_by(title='Условия').first()
            assert l is not None
            assert l.theory_url is None

    def test_new_lesson_is_closed(self, app, logged_in_client):
        logged_in_client.post('/teacher/lessons/create', data={
            'order_number': '1',
            'title': 'Test',
            'theory_url': ''
        })
        with app.app_context():
            l = Lesson.query.first()
            assert l.is_open is False


class TestEditLesson:
    def test_get_edit_form(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Old')
            db.session.add(l)
            db.session.commit()
            lid = l.id
        response = logged_in_client.get(f'/teacher/lessons/{lid}/edit')
        assert response.status_code == 200

    def test_edit_lesson(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Old')
            db.session.add(l)
            db.session.commit()
            lid = l.id
        response = logged_in_client.post(f'/teacher/lessons/{lid}/edit', data={
            'order_number': '5',
            'title': 'New Title',
            'theory_url': 'https://new.url'
        })
        assert response.status_code == 302
        with app.app_context():
            l = db.session.get(Lesson, lid)
            assert l.order_number == 5
            assert l.title == 'New Title'
            assert l.theory_url == 'https://new.url'

    def test_edit_404(self, logged_in_client):
        response = logged_in_client.get('/teacher/lessons/9999/edit')
        assert response.status_code == 404


class TestDeleteLesson:
    def test_delete_lesson(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Test')
            db.session.add(l)
            db.session.commit()
            lid = l.id
        response = logged_in_client.post(f'/teacher/lessons/{lid}/delete')
        assert response.status_code == 302
        with app.app_context():
            assert db.session.get(Lesson, lid) is None


class TestAccessControl:
    def test_open_lesson_with_days(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Test', is_open=False)
            db.session.add(l)
            db.session.commit()
            lid = l.id
        response = logged_in_client.post(f'/teacher/lessons/{lid}/access', data={
            'action': 'open',
            'access_days': '7'
        })
        assert response.status_code == 302
        with app.app_context():
            l = db.session.get(Lesson, lid)
            assert l.is_open is True
            assert l.access_days == 7
            assert l.opened_at is not None

    def test_open_lesson_forever(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Test', is_open=False)
            db.session.add(l)
            db.session.commit()
            lid = l.id
        response = logged_in_client.post(f'/teacher/lessons/{lid}/access', data={
            'action': 'open',
            'access_days': ''
        })
        assert response.status_code == 302
        with app.app_context():
            l = db.session.get(Lesson, lid)
            assert l.is_open is True
            assert l.access_days is None

    def test_close_lesson(self, app, logged_in_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Test', is_open=True, access_days=7)
            db.session.add(l)
            db.session.commit()
            lid = l.id
        response = logged_in_client.post(f'/teacher/lessons/{lid}/access', data={
            'action': 'close'
        })
        assert response.status_code == 302
        with app.app_context():
            l = db.session.get(Lesson, lid)
            assert l.is_open is False


class TestStudentLessonList:
    def test_student_sees_open_lesson(self, app, client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash=generate_password_hash('abc123'),
                password_plain='abc123',
                last_name='Иванов', first_name='Иван', seq_number=1
            )
            db.session.add(s)
            l = Lesson(order_number=1, title='Открытый урок',
                       is_open=True, access_days=None,
                       opened_at=datetime.now(timezone.utc))
            db.session.add(l)
            db.session.commit()
        client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
        response = client.get('/lessons')
        assert response.status_code == 200
        assert b'\xd0\x9e\xd1\x82\xd0\xba\xd1\x80\xd1\x8b\xd1\x82\xd1\x8b\xd0\xb9 \xd1\x83\xd1\x80\xd0\xbe\xd0\xba' in response.data

    def test_student_does_not_see_closed_lesson(self, app, client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash=generate_password_hash('abc123'),
                password_plain='abc123',
                last_name='Иванов', first_name='Иван', seq_number=1
            )
            db.session.add(s)
            l = Lesson(order_number=1, title='Закрытый урок', is_open=False)
            db.session.add(l)
            db.session.commit()
        client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
        response = client.get('/lessons')
        assert response.status_code == 200
        assert b'\xd0\x97\xd0\xb0\xd0\xba\xd1\x80\xd1\x8b\xd1\x82\xd1\x8b\xd0\xb9 \xd1\x83\xd1\x80\xd0\xbe\xd0\xba' not in response.data

    def test_student_does_not_see_expired_lesson(self, app, client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash=generate_password_hash('abc123'),
                password_plain='abc123',
                last_name='Иванов', first_name='Иван', seq_number=1
            )
            db.session.add(s)
            l = Lesson(
                order_number=1, title='Просроченный урок',
                is_open=True, access_days=1,
                opened_at=datetime.now(timezone.utc) - timedelta(days=10)
            )
            db.session.add(l)
            db.session.commit()
        client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
        response = client.get('/lessons')
        assert response.status_code == 200
        assert b'\xd0\x9f\xd1\x80\xd0\xbe\xd1\x81\xd1\x80\xd0\xbe\xd1\x87\xd0\xb5\xd0\xbd\xd0\xbd\xd1\x8b\xd0\xb9 \xd1\x83\xd1\x80\xd0\xbe\xd0\xba' not in response.data
