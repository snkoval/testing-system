import pytest

from app import db
from app.models import Teacher, Group, Student
from werkzeug.security import generate_password_hash


@pytest.fixture
def teacher(app):
    with app.app_context():
        t = Teacher(username='admin', password_hash=generate_password_hash('secret123'))
        db.session.add(t)
        db.session.commit()
        return t


@pytest.fixture
def student(app):
    with app.app_context():
        g = Group(name='7A_1gr')
        db.session.add(g)
        db.session.commit()
        s = Student(
            group_id=g.id,
            login='7A_1gr_1',
            password_hash=generate_password_hash('abc123'),
            password_plain='abc123',
            last_name='Иванов',
            first_name='Иван',
            seq_number=1
        )
        db.session.add(s)
        db.session.commit()
        return s


class TestTeacherLogin:
    def test_get_admin_page(self, client):
        response = client.get('/admin')
        assert response.status_code == 200
        assert b'\xd0\xbb\xd0\xbe\xd0\xb3\xd0\xb8\xd0\xbd' in response.data or \
               b'\xd0\x9b\xd0\xbe\xd0\xb3\xd0\xb8\xd0\xbd' in response.data or \
               b'login' in response.data.lower()

    def test_login_success(self, client, teacher):
        response = client.post('/admin', data={
            'username': 'admin',
            'password': 'secret123'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_login_wrong_password(self, client, teacher):
        response = client.post('/admin', data={
            'username': 'admin',
            'password': 'wrong'
        })
        assert response.status_code == 200
        assert b'\xd0\xbe\xd1\x88\xd0\xb8\xd0\xb1\xd0\xba' in response.data.lower() or \
               b'error' in response.data.lower() or \
               b'invalid' in response.data.lower()

    def test_login_unknown_user(self, client):
        response = client.post('/admin', data={
            'username': 'nobody',
            'password': '123'
        })
        assert response.status_code == 200

    def test_login_redirects_to_teacher_panel(self, client, teacher):
        response = client.post('/admin', data={
            'username': 'admin',
            'password': 'secret123'
        })
        assert response.status_code == 302
        assert '/teacher' in response.headers['Location']


class TestStudentLogin:
    def test_get_login_page(self, client):
        response = client.get('/login')
        assert response.status_code == 200

    def test_login_success(self, client, student):
        response = client.post('/login', data={
            'login': '7A_1gr_1',
            'password': 'abc123'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_login_wrong_password(self, client, student):
        response = client.post('/login', data={
            'login': '7A_1gr_1',
            'password': 'wrong'
        })
        assert response.status_code == 200

    def test_login_redirects_to_lessons(self, client, student):
        response = client.post('/login', data={
            'login': '7A_1gr_1',
            'password': 'abc123'
        })
        assert response.status_code == 302
        assert '/lessons' in response.headers['Location']


class TestLogout:
    def test_teacher_logout(self, client, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        response = client.get('/logout')
        assert response.status_code == 302

    def test_student_logout(self, client, student):
        client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
        response = client.get('/logout')
        assert response.status_code == 302


class TestAccessDecorators:
    def test_protected_teacher_route_redirects(self, client):
        response = client.get('/teacher/groups')
        assert response.status_code == 302
        assert '/admin' in response.headers['Location']

    def test_protected_student_route_redirects(self, client):
        response = client.get('/lessons')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_teacher_can_access_teacher_panel(self, client, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        response = client.get('/teacher/')
        assert response.status_code == 200

    def test_student_cannot_access_teacher_panel(self, client, student):
        client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
        response = client.get('/teacher/groups')
        assert response.status_code == 302
        assert '/admin' in response.headers['Location']


class TestTeacherChangePassword:
    def test_get_settings_page(self, client, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        response = client.get('/teacher/settings')
        assert response.status_code == 200

    def test_change_password_success(self, client, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        response = client.post('/teacher/settings', data={
            'old_password': 'secret123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        assert response.status_code == 302

    def test_change_password_wrong_old(self, client, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        response = client.post('/teacher/settings', data={
            'old_password': 'wrong',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        assert response.status_code == 200

    def test_change_password_mismatch(self, client, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        response = client.post('/teacher/settings', data={
            'old_password': 'secret123',
            'new_password': 'newpass456',
            'confirm_password': 'different'
        })
        assert response.status_code == 200

    def test_new_password_works_after_change(self, client, app, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        client.post('/teacher/settings', data={
            'old_password': 'secret123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        client.get('/logout')
        response = client.post('/admin', data={
            'username': 'admin',
            'password': 'newpass456'
        })
        assert response.status_code == 302
        assert '/teacher' in response.headers['Location']

    def test_old_password_fails_after_change(self, client, app, teacher):
        client.post('/admin', data={'username': 'admin', 'password': 'secret123'})
        client.post('/teacher/settings', data={
            'old_password': 'secret123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        client.get('/logout')
        response = client.post('/admin', data={
            'username': 'admin',
            'password': 'secret123'
        })
        assert response.status_code == 200
