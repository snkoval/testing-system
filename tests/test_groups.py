import re
import pytest

from app import db
from app.models import Teacher, Group, Student
from app.utils import generate_password, generate_login
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


class TestGeneratePassword:
    def test_length_is_6(self):
        pw = generate_password()
        assert len(pw) == 6

    def test_only_lowercase_digits_special(self):
        pw = generate_password()
        allowed = set('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*')
        assert set(pw).issubset(allowed)

    def test_no_uppercase(self):
        for _ in range(100):
            pw = generate_password()
            assert pw == pw.lower()

    def test_uniqueness(self):
        passwords = {generate_password() for _ in range(100)}
        assert len(passwords) > 90


class TestGenerateLogin:
    def test_format(self):
        login = generate_login('7A_1gr', 1)
        assert login == '7A_1gr_1'

    def test_higher_seq(self):
        login = generate_login('10B_2gr', 15)
        assert login == '10B_2gr_15'


class TestGroupList:
    def test_get_groups_page(self, logged_in_client):
        response = logged_in_client.get('/teacher/groups')
        assert response.status_code == 200

    def test_groups_page_shows_group_name(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        response = logged_in_client.get('/teacher/groups')
        assert b'7A_1gr' in response.data


class TestCreateGroup:
    def test_get_create_form(self, logged_in_client):
        response = logged_in_client.get('/teacher/groups/create')
        assert response.status_code == 200

    def test_create_valid_group(self, logged_in_client):
        response = logged_in_client.post('/teacher/groups/create', data={
            'class_number': '7',
            'class_letter': 'A',
            'group_number': '1'
        })
        assert response.status_code == 302
        assert '/teacher/groups/' in response.headers['Location']

    def test_create_two_digit_class(self, logged_in_client):
        response = logged_in_client.post('/teacher/groups/create', data={
            'class_number': '10',
            'class_letter': 'B',
            'group_number': '2'
        })
        assert response.status_code == 302

    def test_create_duplicate_group(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
        response = logged_in_client.post('/teacher/groups/create', data={
            'class_number': '7',
            'class_letter': 'A',
            'group_number': '1'
        })
        assert response.status_code == 200
        assert b'\xd0\xbe\xd1\x88\xd0\xb8\xd0\xb1\xd0\xba' in response.data.lower() or \
               b'error' in response.data.lower() or b'\xd1\x81\xd1\x83\xd1\x89' in response.data

    def test_create_lowercase_letter_auto_uppercased(self, app, logged_in_client):
        response = logged_in_client.post('/teacher/groups/create', data={
            'class_number': '7',
            'class_letter': 'a',
            'group_number': '1'
        })
        assert response.status_code == 302
        with app.app_context():
            g = Group.query.filter_by(name='7A_1gr').first()
            assert g is not None

    def test_group_name_in_db(self, app, logged_in_client):
        logged_in_client.post('/teacher/groups/create', data={
            'class_number': '7',
            'class_letter': 'A',
            'group_number': '3'
        })
        with app.app_context():
            g = Group.query.filter_by(name='7A_3gr').first()
            assert g is not None


class TestGroupDetail:
    def test_get_group_detail(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        response = logged_in_client.get(f'/teacher/groups/{gid}')
        assert response.status_code == 200

    def test_group_detail_shows_student(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash='h', password_plain='abc123',
                last_name='Иванов', first_name='Иван', seq_number=1
            )
            db.session.add(s)
            db.session.commit()
            gid = g.id
        response = logged_in_client.get(f'/teacher/groups/{gid}')
        assert b'\xd0\x98\xd0\xb2\xd0\xb0\xd0\xbd\xd0\xbe\xd0\xb2' in response.data
        assert b'abc123' in response.data

    def test_group_detail_404(self, logged_in_client):
        response = logged_in_client.get('/teacher/groups/9999')
        assert response.status_code == 404


class TestAddStudent:
    def test_add_single_student(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        response = logged_in_client.post(f'/teacher/groups/{gid}/add', data={
            'last_name': 'Петров',
            'first_name': 'Пётр'
        })
        assert response.status_code == 302
        with app.app_context():
            s = Student.query.filter_by(group_id=gid).first()
            assert s is not None
            assert s.login == '7A_1gr_1'
            assert s.last_name == 'Петров'
            assert s.first_name == 'Пётр'
            assert s.seq_number == 1
            assert len(s.password_plain) == 6

    def test_add_second_student_seq(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        logged_in_client.post(f'/teacher/groups/{gid}/add', data={
            'last_name': 'А', 'first_name': 'А'
        })
        logged_in_client.post(f'/teacher/groups/{gid}/add', data={
            'last_name': 'Б', 'first_name': 'Б'
        })
        with app.app_context():
            students = Student.query.filter_by(group_id=gid).order_by(Student.seq_number).all()
            assert len(students) == 2
            assert students[0].seq_number == 1
            assert students[0].login == '7A_1gr_1'
            assert students[1].seq_number == 2
            assert students[1].login == '7A_1gr_2'


class TestBulkAdd:
    def test_bulk_add_multiple(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        response = logged_in_client.post(f'/teacher/groups/{gid}/bulk-add', data={
            'students_data': 'Иван Иванов\nПётр Петров\nСидор Сидоров'
        })
        assert response.status_code == 200
        with app.app_context():
            students = Student.query.filter_by(group_id=gid).order_by(Student.seq_number).all()
            assert len(students) == 3
            assert students[0].login == '7A_1gr_1'
            assert students[1].login == '7A_1gr_2'
            assert students[2].login == '7A_1gr_3'

    def test_bulk_add_shows_credentials(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        response = logged_in_client.post(f'/teacher/groups/{gid}/bulk-add', data={
            'students_data': 'Иван Иванов'
        })
        assert response.status_code == 200

    def test_bulk_add_with_existing_students(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        logged_in_client.post(f'/teacher/groups/{gid}/add', data={
            'last_name': 'Первый', 'first_name': 'П'
        })
        logged_in_client.post(f'/teacher/groups/{gid}/bulk-add', data={
            'students_data': 'Второй В\nТретий Т'
        })
        with app.app_context():
            students = Student.query.filter_by(group_id=gid).order_by(Student.seq_number).all()
            assert len(students) == 3
            assert students[0].seq_number == 1
            assert students[1].seq_number == 2
            assert students[2].seq_number == 3


class TestStudentPassword:
    def test_change_password(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash=generate_password_hash('old123'),
                password_plain='old123',
                last_name='А', first_name='А', seq_number=1
            )
            db.session.add(s)
            db.session.commit()
            sid = s.id
        response = logged_in_client.post(f'/teacher/students/{sid}/password', data={
            'new_password': 'new456'
        })
        assert response.status_code == 302
        with app.app_context():
            s = db.session.get(Student, sid)
            assert s.password_plain == 'new456'

    def test_reset_password(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash=generate_password_hash('old123'),
                password_plain='old123',
                last_name='А', first_name='А', seq_number=1
            )
            db.session.add(s)
            db.session.commit()
            sid = s.id
        response = logged_in_client.post(f'/teacher/students/{sid}/reset-password')
        assert response.status_code == 302
        with app.app_context():
            s = db.session.get(Student, sid)
            assert s.password_plain != 'old123'
            assert len(s.password_plain) == 6


class TestDeleteGroup:
    def test_delete_group(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
        response = logged_in_client.post(f'/teacher/groups/{gid}/delete')
        assert response.status_code == 302
        assert '/teacher/groups' in response.headers['Location']
        with app.app_context():
            assert db.session.get(Group, gid) is None

    def test_delete_group_cascades_students(self, app, logged_in_client):
        with app.app_context():
            g = Group(name='7A_1gr')
            db.session.add(g)
            db.session.commit()
            gid = g.id
            s = Student(
                group_id=g.id, login='7A_1gr_1',
                password_hash='h', password_plain='abc',
                last_name='А', first_name='А', seq_number=1
            )
            db.session.add(s)
            db.session.commit()
            sid = s.id
        logged_in_client.post(f'/teacher/groups/{gid}/delete')
        with app.app_context():
            assert db.session.get(Student, sid) is None
