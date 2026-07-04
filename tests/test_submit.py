import json
from datetime import datetime, timezone

import pytest

from app import db
from app.models import Group, Student, Lesson, Task, Submission
from app.test_files import add_test
from werkzeug.security import generate_password_hash


@pytest.fixture
def student_client(app, client):
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
        db.session.commit()
        sid = s.id
    client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
    return client, sid


@pytest.fixture
def setup_lesson_task(app):
    with app.app_context():
        l = Lesson(order_number=1, title='Тест', is_open=True,
                   access_days=None,
                   opened_at=datetime.now(timezone.utc))
        db.session.add(l)
        db.session.commit()
        t = Task(lesson_id=l.id, letter_index='A',
                 short_title='Sum', problem_text='Sum of two',
                 input_description='Two ints',
                 output_description='Their sum',
                 time_limit=2, memory_limit=256)
        db.session.add(t)
        db.session.commit()
        add_test(t.id, 1, '2 3\n', '5\n')
        add_test(t.id, 2, '10 20\n', '30\n')
        return l.id, t.id


# ── Submit endpoint ────────────────────────────────────────────────────


class TestSubmitCode:
    def test_submit_correct_python(self, student_client, setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        resp = client.post('/submit', data={
            'task_id': task_id,
            'code': 'a, b = map(int, input().split())\nprint(a + b)\n',
            'language': 'python',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'
        assert data['passed'] == 2
        assert data['total_tests'] == 2

    def test_submit_wrong_answer(self, student_client, setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        resp = client.post('/submit', data={
            'task_id': task_id,
            'code': 'a, b = map(int, input().split())\nprint(a * b)\n',
            'language': 'python',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'error'
        assert data['passed'] == 0

    def test_submit_saves_submission(self, app, student_client,
                                      setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        client.post('/submit', data={
            'task_id': task_id,
            'code': 'print(42)',
            'language': 'python',
        })
        with app.app_context():
            sub = Submission.query.filter_by(
                student_id=sid, task_id=task_id).first()
            assert sub is not None
            assert sub.code == 'print(42)'
            assert sub.language == 'python'

    def test_submit_overwrites_previous(self, app, student_client,
                                         setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        client.post('/submit', data={
            'task_id': task_id,
            'code': 'print(1)',
            'language': 'python',
        })
        client.post('/submit', data={
            'task_id': task_id,
            'code': 'print(2)',
            'language': 'python',
        })
        with app.app_context():
            subs = Submission.query.filter_by(
                student_id=sid, task_id=task_id).all()
            assert len(subs) == 1
            assert subs[0].code == 'print(2)'

    def test_submit_returns_results_list(self, student_client,
                                          setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        resp = client.post('/submit', data={
            'task_id': task_id,
            'code': 'a, b = map(int, input().split())\nprint(a + b)\n',
            'language': 'python',
        })
        data = resp.get_json()
        assert 'results' in data
        assert len(data['results']) == 2
        for r in data['results']:
            assert 'number' in r
            assert 'status' in r
            assert 'message' in r

    def test_submit_compile_error_in_response(self, student_client,
                                               setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        resp = client.post('/submit', data={
            'task_id': task_id,
            'code': 'invalid syntax !!!',
            'language': 'python',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_submit_requires_login(self, client, setup_lesson_task):
        lesson_id, task_id = setup_lesson_task
        resp = client.post('/submit', data={
            'task_id': task_id,
            'code': 'print(1)',
            'language': 'python',
        })
        assert resp.status_code == 302

    def test_submit_missing_task_id(self, student_client):
        client, sid = student_client
        resp = client.post('/submit', data={
            'code': 'print(1)',
            'language': 'python',
        })
        assert resp.status_code == 404

    def test_submit_missing_code(self, student_client, setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        resp = client.post('/submit', data={
            'task_id': task_id,
            'language': 'python',
        })
        assert resp.status_code == 400


class TestSubmitAccessControl:
    def test_submit_closed_lesson(self, app, student_client):
        client, sid = student_client
        with app.app_context():
            l = Lesson(order_number=2, title='Closed', is_open=False)
            db.session.add(l)
            db.session.commit()
            t = Task(lesson_id=l.id, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            add_test(t.id, 1, '1\n', '1\n')
            add_test(t.id, 2, '2\n', '2\n')
            tid = t.id
        resp = client.post('/submit', data={
            'task_id': tid,
            'code': 'print(1)',
            'language': 'python',
        })
        assert resp.status_code == 403


# ── Load saved code ────────────────────────────────────────────────────


class TestLoadSavedCode:
    def test_task_ajax_returns_saved_code(self, app, student_client,
                                           setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        client.post('/submit', data={
            'task_id': task_id,
            'code': 'a, b = map(int, input().split())\nprint(a + b)\n',
            'language': 'python',
        })
        resp = client.get(f'/lessons/{lesson_id}/tasks/{task_id}')
        assert resp.status_code == 200
        text = resp.data.decode('utf-8')
        assert 'a, b = map(int' in text

    def test_task_ajax_returns_saved_language(self, app, student_client,
                                               setup_lesson_task):
        client, sid = student_client
        lesson_id, task_id = setup_lesson_task
        client.post('/submit', data={
            'task_id': task_id,
            'code': 'print(42)',
            'language': 'python',
        })
        resp = client.get(f'/lessons/{lesson_id}/tasks/{task_id}')
        text = resp.data.decode('utf-8')
        assert 'python' in text.lower()
