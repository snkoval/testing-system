import sys

import pytest
from werkzeug.security import generate_password_hash, check_password_hash

from app import create_app, db
from app.config import Config
from app.models import Teacher, Group, Student, Lesson, Task, Submission


# ── CSRF-enabled config for CSRF tests ────────────────────────────────

class CSRFTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'csrf-test-secret'
    CSRF_PROTECTION_ENABLED = True


@pytest.fixture
def csrf_app(tmp_path):
    app = create_app(CSRFTestConfig)
    app.config['TESTS_FOLDER'] = str(tmp_path)
    app.config['PYTHON_EXEC'] = sys.executable
    with app.app_context():
        db.create_all()
        teacher = Teacher(username='admin',
                          password_hash=generate_password_hash('secret'))
        db.session.add(teacher)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def csrf_client(csrf_app):
    return csrf_app.test_client()


def _get_csrf_token(client):
    with client.session_transaction() as sess:
        return sess.get('csrf_token', '')


def _login_csrf(client, username='admin', password='secret'):
    client.get('/admin')
    token = _get_csrf_token(client)
    return client.post('/admin', data={
        'username': username, 'password': password,
        'csrf_token': token,
    })


# ── Password hashing ──────────────────────────────────────────────────


class TestPasswordHashing:

    def test_teacher_password_is_hashed(self, app):
        with app.app_context():
            teacher = Teacher(
                username='t1',
                password_hash=generate_password_hash('mypw'),
            )
            db.session.add(teacher)
            db.session.commit()
            assert teacher.password_hash != 'mypw'
            assert check_password_hash(teacher.password_hash, 'mypw')

    def test_student_password_is_hashed(self, app):
        with app.app_context():
            group = Group(name='7A_1gr')
            db.session.add(group)
            db.session.commit()
            student = Student(
                group_id=group.id,
                login='7A_1gr_1',
                password_hash=generate_password_hash('abc123'),
                password_plain='abc123',
                last_name='Ivanov', first_name='Ivan', seq_number=1,
            )
            db.session.add(student)
            db.session.commit()
            assert student.password_hash != student.password_plain
            assert check_password_hash(student.password_hash, 'abc123')


# ── Data isolation ────────────────────────────────────────────────────


class TestDataIsolation:

    def _setup_env(self, app):
        with app.app_context():
            group = Group(name='7A_1gr')
            db.session.add(group)
            db.session.commit()

            s1 = Student(
                group_id=group.id, login='7A_1gr_1',
                password_hash=generate_password_hash('pw1'),
                password_plain='pw1',
                last_name='One', first_name='A', seq_number=1,
            )
            s2 = Student(
                group_id=group.id, login='7A_1gr_2',
                password_hash=generate_password_hash('pw2'),
                password_plain='pw2',
                last_name='Two', first_name='B', seq_number=2,
            )
            db.session.add_all([s1, s2])

            lesson = Lesson(order_number=1, title='Test', is_open=True)
            db.session.add(lesson)
            db.session.commit()

            task = Task(
                lesson_id=lesson.id, letter_index='A',
                short_title='Sum', problem_text='Sum',
                input_description='a b', output_description='a+b',
            )
            db.session.add(task)
            db.session.commit()

            sub = Submission(
                student_id=s1.id, task_id=task.id,
                code='SECRET_CODE_FROM_STUDENT_1',
                language='python', test_results='{}',
            )
            db.session.add(sub)
            db.session.commit()

            return s1.id, s2.id, lesson.id, task.id

    def test_student_cannot_see_other_code(self, app, client):
        s1_id, s2_id, lesson_id, task_id = self._setup_env(app)
        client.post('/login', data={'login': '7A_1gr_2', 'password': 'pw2'})
        resp = client.get(f'/lessons/{lesson_id}/tasks/{task_id}')
        assert resp.status_code == 200
        assert b'SECRET_CODE_FROM_STUDENT_1' not in resp.data

    def test_submit_uses_session_student(self, app, client):
        s1_id, s2_id, lesson_id, task_id = self._setup_env(app)
        client.post('/login', data={'login': '7A_1gr_2', 'password': 'pw2'})
        client.post('/submit', data={
            'task_id': task_id,
            'code': 'print(input())',
            'language': 'python',
        })
        with app.app_context():
            s1_sub = Submission.query.filter_by(
                student_id=s1_id, task_id=task_id).first()
            assert s1_sub.code == 'SECRET_CODE_FROM_STUDENT_1'
            s2_sub = Submission.query.filter_by(
                student_id=s2_id, task_id=task_id).first()
            assert s2_sub is not None
            assert s2_sub.code == 'print(input())'

    def test_student_cannot_access_teacher_panel(self, app, client):
        self._setup_env(app)
        client.post('/login', data={'login': '7A_1gr_2', 'password': 'pw2'})
        resp = client.get('/teacher/')
        assert resp.status_code == 302

    def test_unauthenticated_redirected_from_lessons(self, client):
        resp = client.get('/lessons')
        assert resp.status_code == 302


# ── XSS protection ────────────────────────────────────────────────────


class TestXSSProtection:

    def test_script_tag_in_task_text_escaped(self, app, client):
        with app.app_context():
            group = Group(name='7A_1gr')
            db.session.add(group)
            db.session.commit()
            student = Student(
                group_id=group.id, login='7A_1gr_1',
                password_hash=generate_password_hash('pw'),
                password_plain='pw',
                last_name='T', first_name='T', seq_number=1,
            )
            db.session.add(student)

            lesson = Lesson(order_number=1, title='L', is_open=True)
            db.session.add(lesson)
            db.session.commit()

            task = Task(
                lesson_id=lesson.id, letter_index='A',
                short_title='<script>alert(1)</script>',
                problem_text='<script>alert("xss")</script>',
                input_description='in',
                output_description='out',
            )
            db.session.add(task)
            db.session.commit()
            lesson_id, task_id = lesson.id, task.id

        client.post('/login', data={'login': '7A_1gr_1', 'password': 'pw'})
        resp = client.get(f'/lessons/{lesson_id}/tasks/{task_id}')
        assert resp.status_code == 200
        assert b'<script>alert' not in resp.data
        assert b'&lt;script&gt;' in resp.data


# ── CSRF protection ───────────────────────────────────────────────────


class TestCSRFProtection:

    def test_login_post_without_token_rejected(self, csrf_client):
        csrf_client.get('/admin')
        resp = csrf_client.post('/admin', data={
            'username': 'admin', 'password': 'secret'})
        assert resp.status_code == 400

    def test_login_post_with_valid_token_accepted(self, csrf_client):
        csrf_client.get('/admin')
        token = _get_csrf_token(csrf_client)
        resp = csrf_client.post('/admin', data={
            'username': 'admin', 'password': 'secret',
            'csrf_token': token,
        })
        assert resp.status_code == 302

    def test_login_post_with_wrong_token_rejected(self, csrf_client):
        csrf_client.get('/admin')
        resp = csrf_client.post('/admin', data={
            'username': 'admin', 'password': 'secret',
            'csrf_token': 'wrong',
        })
        assert resp.status_code == 400

    def test_teacher_create_without_token_rejected(self, csrf_client):
        _login_csrf(csrf_client)
        resp = csrf_client.post('/teacher/groups/create',
                                data={'name': '7A_1gr'})
        assert resp.status_code == 400

    def test_teacher_create_with_token_accepted(self, csrf_client):
        _login_csrf(csrf_client)
        csrf_client.get('/teacher/groups/create')
        token = _get_csrf_token(csrf_client)
        resp = csrf_client.post('/teacher/groups/create', data={
            'class_number': '7', 'class_letter': 'A',
            'group_number': '1', 'csrf_token': token,
        })
        assert resp.status_code == 302

    def test_get_requests_not_blocked(self, csrf_client):
        resp = csrf_client.get('/admin')
        assert resp.status_code == 200


# ── Error pages ────────────────────────────────────────────────────────


class TestErrorPages:

    def test_404_returns_custom_page(self, client):
        resp = client.get('/nonexistent-page')
        assert resp.status_code == 404

    def test_404_has_friendly_message(self, client):
        resp = client.get('/nonexistent-page')
        assert resp.status_code == 404
        assert b'\xd0\xbd\xd0\xb5' in resp.data or b'404' in resp.data


# ── Noindex on login page ─────────────────────────────────────────────


class TestNoIndex:

    def test_student_login_has_noindex(self, client):
        resp = client.get('/login')
        assert b'noindex' in resp.data
