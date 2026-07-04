import pytest

from app import db
from app.models import Teacher, Group, Student, Lesson, Task, Submission
from app.test_files import get_tests, get_test_count, get_test_dir
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


@pytest.fixture
def lesson(app):
    with app.app_context():
        l = Lesson(order_number=1, title='Урок 1')
        db.session.add(l)
        db.session.commit()
        return l.id


# ── Task list ──────────────────────────────────────────────────────────


class TestTaskList:
    def test_get_tasks_page(self, logged_in_client, lesson):
        resp = logged_in_client.get(f'/teacher/lessons/{lesson}/tasks')
        assert resp.status_code == 200

    def test_tasks_page_shows_task(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='Сумма', problem_text='p',
                     input_description='in', output_description='out')
            db.session.add(t)
            db.session.commit()
        resp = logged_in_client.get(f'/teacher/lessons/{lesson}/tasks')
        assert b'\xd0\xa1\xd1\x83\xd0\xbc\xd0\xbc\xd0\xb0' in resp.data

    def test_tasks_page_404(self, logged_in_client):
        resp = logged_in_client.get('/teacher/lessons/9999/tasks')
        assert resp.status_code == 404

    def test_tasks_page_shows_test_count(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='in', output_description='out')
            db.session.add(t)
            db.session.commit()
            tid = t.id
            from app.test_files import add_test
            add_test(tid, 1, '1 2', '3')
            add_test(tid, 2, '3 4', '7')
        resp = logged_in_client.get(f'/teacher/lessons/{lesson}/tasks')
        assert b'2' in resp.data


# ── Create task ────────────────────────────────────────────────────────


class TestCreateTask:
    def test_get_create_form(self, logged_in_client, lesson):
        resp = logged_in_client.get(f'/teacher/lessons/{lesson}/tasks/create')
        assert resp.status_code == 200

    def test_create_task_default_limits(self, app, logged_in_client, lesson):
        resp = logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': 'Задача A',
            'problem_text': 'Найдите сумму',
            'input_description': 'Два числа',
            'output_description': 'Сумма',
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            task = Task.query.filter_by(lesson_id=lesson).first()
            assert task is not None
            assert task.short_title == 'Задача A'
            assert task.letter_index == 'A'
            assert task.time_limit == 1
            assert task.memory_limit == 256

    def test_create_task_custom_limits(self, app, logged_in_client, lesson):
        logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': 'Задача',
            'problem_text': 'Условие',
            'input_description': 'Входные',
            'output_description': 'Результат',
            'time_limit': '2',
            'memory_limit': '512',
        })
        with app.app_context():
            task = Task.query.filter_by(lesson_id=lesson).first()
            assert task.time_limit == 2
            assert task.memory_limit == 512

    def test_first_task_gets_letter_a(self, app, logged_in_client, lesson):
        logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': 'T1', 'problem_text': 'p',
            'input_description': 'i', 'output_description': 'o',
        })
        with app.app_context():
            task = Task.query.filter_by(lesson_id=lesson).first()
            assert task.letter_index == 'A'

    def test_second_task_gets_letter_b(self, app, logged_in_client, lesson):
        for title in ('T1', 'T2'):
            logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
                'short_title': title, 'problem_text': 'p',
                'input_description': 'i', 'output_description': 'o',
            })
        with app.app_context():
            tasks = Task.query.filter_by(lesson_id=lesson).order_by(Task.id).all()
            assert tasks[0].letter_index == 'A'
            assert tasks[1].letter_index == 'B'

    def test_create_21st_task_fails(self, app, logged_in_client, lesson):
        for i in range(20):
            logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
                'short_title': f'T{i}', 'problem_text': 'p',
                'input_description': 'i', 'output_description': 'o',
            })
        resp = logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': 'T21', 'problem_text': 'p',
            'input_description': 'i', 'output_description': 'o',
        })
        with app.app_context():
            assert Task.query.filter_by(lesson_id=lesson).count() == 20
        assert resp.status_code == 200  # returns form with error

    def test_create_without_short_title_fails(self, app, logged_in_client, lesson):
        resp = logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': '', 'problem_text': 'p',
            'input_description': 'i', 'output_description': 'o',
        })
        with app.app_context():
            assert Task.query.filter_by(lesson_id=lesson).count() == 0

    def test_create_without_problem_text_fails(self, app, logged_in_client, lesson):
        resp = logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': 'T', 'problem_text': '',
            'input_description': 'i', 'output_description': 'o',
        })
        with app.app_context():
            assert Task.query.filter_by(lesson_id=lesson).count() == 0

    def test_create_task_redirects_to_tasks_list(self, logged_in_client, lesson):
        resp = logged_in_client.post(f'/teacher/lessons/{lesson}/tasks/create', data={
            'short_title': 'T', 'problem_text': 'p',
            'input_description': 'i', 'output_description': 'o',
        })
        assert resp.status_code == 302
        assert f'/teacher/lessons/{lesson}/tasks' in resp.headers['Location']


# ── Edit task ──────────────────────────────────────────────────────────


class TestEditTask:
    def test_get_edit_form(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='Старое', problem_text='p',
                     input_description='in', output_description='out')
            db.session.add(t)
            db.session.commit()
            tid = t.id
        resp = logged_in_client.get(f'/teacher/tasks/{tid}/edit')
        assert resp.status_code == 200

    def test_edit_task(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='Старое', problem_text='p',
                     input_description='in', output_description='out')
            db.session.add(t)
            db.session.commit()
            tid = t.id
        logged_in_client.post(f'/teacher/tasks/{tid}/edit', data={
            'short_title': 'Новое', 'problem_text': 'new problem',
            'input_description': 'new in', 'output_description': 'new out',
            'time_limit': '5', 'memory_limit': '128',
        })
        with app.app_context():
            task = db.session.get(Task, tid)
            assert task.short_title == 'Новое'
            assert task.problem_text == 'new problem'
            assert task.time_limit == 5
            assert task.memory_limit == 128
            assert task.letter_index == 'A'

    def test_edit_404(self, logged_in_client):
        resp = logged_in_client.get('/teacher/tasks/9999/edit')
        assert resp.status_code == 404


# ── Delete task ────────────────────────────────────────────────────────


class TestDeleteTask:
    def test_delete_task(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
        resp = logged_in_client.post(f'/teacher/tasks/{tid}/delete')
        assert resp.status_code == 302
        with app.app_context():
            assert db.session.get(Task, tid) is None

    def test_delete_task_404(self, logged_in_client):
        resp = logged_in_client.post('/teacher/tasks/9999/delete')
        assert resp.status_code == 404


# ── Manage tests ───────────────────────────────────────────────────────


class TestManageTests:
    def test_get_tests_page(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
        resp = logged_in_client.get(f'/teacher/tasks/{tid}/tests')
        assert resp.status_code == 200

    def test_get_tests_page_404(self, logged_in_client):
        resp = logged_in_client.get('/teacher/tasks/9999/tests')
        assert resp.status_code == 404

    def test_add_test(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
        logged_in_client.post(f'/teacher/tasks/{tid}/tests', data={
            'action': 'add',
            'input_data': '5 3',
            'expected_output': '8',
        })
        tests = get_tests(tid)
        assert len(tests) == 1
        assert tests[0][0] == 1
        assert tests[0][1] == '5 3'
        assert tests[0][2] == '8'

    def test_add_multiple_tests(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
        for i in range(1, 4):
            logged_in_client.post(f'/teacher/tasks/{tid}/tests', data={
                'action': 'add',
                'input_data': f'in{i}',
                'expected_output': f'out{i}',
            })
        tests = get_tests(tid)
        assert len(tests) == 3
        assert tests[0][0] == 1
        assert tests[1][0] == 2
        assert tests[2][0] == 3

    def test_edit_test(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i',
                     output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
            from app.test_files import add_test
            add_test(tid, 1, 'old_in', 'old_out')
        logged_in_client.post(f'/teacher/tasks/{tid}/tests', data={
            'action': 'edit',
            'test_num': '1',
            'input_data': 'new_in',
            'expected_output': 'new_out',
        })
        tests = get_tests(tid)
        assert len(tests) == 1
        assert tests[0][1] == 'new_in'
        assert tests[0][2] == 'new_out'

    def test_delete_test(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
            from app.test_files import add_test
            add_test(tid, 1, 'in1', 'out1')
            add_test(tid, 2, 'in2', 'out2')
            add_test(tid, 3, 'in3', 'out3')
        logged_in_client.post(f'/teacher/tasks/{tid}/tests', data={
            'action': 'delete',
            'test_num': '2',
        })
        tests = get_tests(tid)
        assert len(tests) == 2
        nums = [t[0] for t in tests]
        assert 2 not in nums

    def test_cannot_delete_when_only_two_tests(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
            from app.test_files import add_test
            add_test(tid, 1, 'in1', 'out1')
            add_test(tid, 2, 'in2', 'out2')
        resp = logged_in_client.post(f'/teacher/tasks/{tid}/tests', data={
            'action': 'delete',
            'test_num': '1',
        })
        tests = get_tests(tid)
        assert len(tests) == 2

    def test_tests_page_shows_preview(self, app, logged_in_client, lesson):
        with app.app_context():
            t = Task(lesson_id=lesson, letter_index='A',
                     short_title='X', problem_text='p',
                     input_description='i', output_description='o')
            db.session.add(t)
            db.session.commit()
            tid = t.id
            from app.test_files import add_test
            add_test(tid, 1, 'hello', 'world')
        resp = logged_in_client.get(f'/teacher/tasks/{tid}/tests')
        assert b'hello' in resp.data
        assert b'world' in resp.data
