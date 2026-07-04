from datetime import datetime, timezone, timedelta

import pytest

from app import db
from app.models import Group, Student, Lesson, Task
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
    client.post('/login', data={'login': '7A_1gr_1', 'password': 'abc123'})
    return client


@pytest.fixture
def open_lesson(app):
    with app.app_context():
        l = Lesson(order_number=1, title='Переменные и типы',
                   is_open=True, access_days=None,
                   opened_at=datetime.now(timezone.utc))
        db.session.add(l)
        db.session.commit()
        return l.id


@pytest.fixture
def lesson_with_task(app, open_lesson):
    with app.app_context():
        t = Task(
            lesson_id=open_lesson,
            letter_index='A',
            short_title='Сумма двух чисел',
            problem_text='Даны два целых числа. Найдите их сумму.',
            input_description='На вход подаются два целых числа',
            output_description='Выведите сумму этих чисел',
            notes='Числа по модулю не превышают 10^9',
            time_limit=1,
            memory_limit=256,
        )
        db.session.add(t)
        db.session.commit()
        add_test(t.id, 1, '2 3', '5')
        add_test(t.id, 2, '10 20', '30')
        return t.id


# ── Lesson page ────────────────────────────────────────────────────────


class TestLessonPage:
    def test_get_lesson_page(self, student_client, open_lesson):
        resp = student_client.get(f'/lessons/{open_lesson}')
        assert resp.status_code == 200

    def test_lesson_page_shows_title(self, student_client, open_lesson):
        resp = student_client.get(f'/lessons/{open_lesson}')
        title = 'Переменные и типы'.encode('utf-8')
        assert title in resp.data

    def test_lesson_page_404(self, student_client):
        resp = student_client.get('/lessons/9999')
        assert resp.status_code == 404

    def test_closed_lesson_redirects(self, app, student_client):
        with app.app_context():
            l = Lesson(order_number=2, title='Закрытый', is_open=False)
            db.session.add(l)
            db.session.commit()
            lid = l.id
        resp = student_client.get(f'/lessons/{lid}')
        assert resp.status_code == 302

    def test_expired_lesson_redirects(self, app, student_client):
        with app.app_context():
            l = Lesson(
                order_number=3, title='Просроченный',
                is_open=True, access_days=1,
                opened_at=datetime.now(timezone.utc) - timedelta(days=10)
            )
            db.session.add(l)
            db.session.commit()
            lid = l.id
        resp = student_client.get(f'/lessons/{lid}')
        assert resp.status_code == 302


# ── Lesson page shows tasks ────────────────────────────────────────────


class TestLessonPageTasks:
    def test_lesson_page_shows_task_list(self, student_client, open_lesson,
                                          lesson_with_task):
        resp = student_client.get(f'/lessons/{open_lesson}')
        task_title = 'Сумма двух чисел'.encode('utf-8')
        assert task_title in resp.data

    def test_lesson_page_shows_letter_index(self, student_client, open_lesson,
                                             lesson_with_task):
        resp = student_client.get(f'/lessons/{open_lesson}')
        assert b'A.' in resp.data or b'A ' in resp.data

    def test_lesson_page_shows_theory_url(self, app, student_client):
        with app.app_context():
            l = Lesson(order_number=1, title='Тест',
                       is_open=True, access_days=None,
                       opened_at=datetime.now(timezone.utc),
                       theory_url='https://example.com/theory')
            db.session.add(l)
            db.session.commit()
            lid = l.id
        resp = student_client.get(f'/lessons/{lid}')
        assert b'https://example.com/theory' in resp.data


# ── AJAX task endpoint ─────────────────────────────────────────────────


class TestTaskAjax:
    def test_get_task_statement(self, student_client, open_lesson,
                                 lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        assert resp.status_code == 200

    def test_task_statement_shows_problem_text(self, student_client,
                                                open_lesson,
                                                lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        problem = 'Даны два целых числа'.encode('utf-8')
        assert problem in resp.data

    def test_task_statement_shows_limits(self, student_client, open_lesson,
                                          lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        assert b'1' in resp.data
        assert b'256' in resp.data

    def test_task_statement_shows_input_desc(self, student_client,
                                              open_lesson,
                                              lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        desc = 'На вход подаются два целых числа'.encode('utf-8')
        assert desc in resp.data

    def test_task_statement_shows_output_desc(self, student_client,
                                               open_lesson,
                                               lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        desc = 'Выведите сумму этих чисел'.encode('utf-8')
        assert desc in resp.data

    def test_task_statement_shows_examples(self, student_client,
                                            open_lesson,
                                            lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        assert b'2 3' in resp.data
        assert b'5' in resp.data
        assert b'10 20' in resp.data
        assert b'30' in resp.data

    def test_task_statement_shows_notes(self, student_client, open_lesson,
                                         lesson_with_task):
        resp = student_client.get(
            f'/lessons/{open_lesson}/tasks/{lesson_with_task}')
        notes = 'Числа по модулю не превышают 10^9'.encode('utf-8')
        assert notes in resp.data

    def test_task_ajax_404_bad_lesson(self, student_client, lesson_with_task):
        resp = student_client.get(f'/lessons/9999/tasks/{lesson_with_task}')
        assert resp.status_code == 404

    def test_task_ajax_404_bad_task(self, student_client, open_lesson):
        resp = student_client.get(f'/lessons/{open_lesson}/tasks/9999')
        assert resp.status_code == 404

    def test_task_ajax_task_not_in_lesson(self, app, student_client,
                                           open_lesson, lesson_with_task):
        with app.app_context():
            l2 = Lesson(order_number=2, title='Другой урок',
                        is_open=True, access_days=None,
                        opened_at=datetime.now(timezone.utc))
            db.session.add(l2)
            db.session.commit()
            l2id = l2.id
        resp = student_client.get(
            f'/lessons/{l2id}/tasks/{lesson_with_task}')
        assert resp.status_code == 404


# ── Editor present ─────────────────────────────────────────────────────


class TestEditor:
    def test_lesson_page_has_language_selector(self, student_client,
                                                 open_lesson,
                                                 lesson_with_task):
        resp = student_client.get(f'/lessons/{open_lesson}')
        assert b'python' in resp.data.lower()
        assert b'cpp' in resp.data.lower() or b'c++' in resp.data.lower()

    def test_lesson_page_has_submit_button(self, student_client, open_lesson,
                                            lesson_with_task):
        resp = student_client.get(f'/lessons/{open_lesson}')
        text = resp.data.decode('utf-8')
        assert 'проверить' in text.lower() or 'отправить' in text.lower()

    def test_lesson_page_has_textarea(self, student_client, open_lesson,
                                       lesson_with_task):
        resp = student_client.get(f'/lessons/{open_lesson}')
        assert b'<textarea' in resp.data or b'editor' in resp.data.lower()
