import shutil
import sys

import pytest

from app import db
from app.models import Lesson, Task
from app.test_files import add_test
from app.checker import check_submission


PYTHON_EXEC = sys.executable


@pytest.fixture
def lesson(app):
    with app.app_context():
        l = Lesson(order_number=1, title='Test Lesson')
        db.session.add(l)
        db.session.commit()
        return l.id


@pytest.fixture
def task_with_tests(app, lesson):
    with app.app_context():
        t = Task(
            lesson_id=lesson,
            letter_index='A',
            short_title='Sum',
            problem_text='Sum of two numbers',
            input_description='Two integers',
            output_description='Their sum',
            time_limit=2,
            memory_limit=262144,
        )
        db.session.add(t)
        db.session.commit()
        add_test(t.id, 1, '2 3\n', '5\n')
        add_test(t.id, 2, '10 20\n', '30\n')
        add_test(t.id, 3, '-5 5\n', '0\n')
        return t.id


# ── Python tests ───────────────────────────────────────────────────────


class TestPythonCorrect:
    def test_all_tests_pass(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a + b)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert result['status'] == 'ok'
        assert result['total_tests'] == 3
        assert result['passed'] == 3
        assert result['compile_error'] is None
        for r in result['results']:
            assert r['status'] == 'passed'


class TestPythonWrongAnswer:
    def test_wrong_answer(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a * b)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert result['status'] == 'error'
        assert result['passed'] == 0
        failed = [r for r in result['results'] if r['status'] == 'failed']
        assert len(failed) == 3


class TestPythonPartial:
    def test_partial_pass(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a + b + 1)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert result['status'] == 'error'
        assert result['passed'] == 0
        statuses = [r['status'] for r in result['results']]
        assert statuses.count('failed') == 3


class TestPythonTimeLimit:
    def test_infinite_loop_tle(self, app, task_with_tests):
        code = 'while True:\n    pass\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert result['status'] == 'error'
        assert result['passed'] == 0
        tle = [r for r in result['results']
               if r['status'] == 'time_limit']
        assert len(tle) == 3


class TestPythonRuntimeError:
    def test_runtime_error(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a + b)\nraise SystemExit(1)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert result['status'] == 'error'


class TestPythonEmptyInput:
    def test_code_with_no_output(self, app, task_with_tests):
        code = 'input()\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert result['status'] == 'error'
        assert result['passed'] == 0


@pytest.fixture
def task_low_memory(app, lesson):
    with app.app_context():
        t = Task(
            lesson_id=lesson,
            letter_index='B',
            short_title='Mem',
            problem_text='Memory test',
            input_description='None',
            output_description='ok',
            time_limit=5,
            memory_limit=40960,
        )
        db.session.add(t)
        db.session.commit()
        add_test(t.id, 1, '', 'ok\n')
        return t.id


class TestPythonMemoryLimit:
    def test_memory_exceeded(self, app, task_low_memory):
        code = (
            'x = bytearray(100 * 1024 * 1024)\n'
            'import time; time.sleep(2)\n'
            'print("ok")\n'
        )
        with app.app_context():
            result = check_submission(code, 'python', task_low_memory)
        assert result['status'] == 'error'
        ml = [r for r in result['results']
              if r['status'] == 'memory_limit']
        assert len(ml) == 1


# ── C++ tests (skipped if g++ not available) ───────────────────────────


has_cpp = shutil.which('g++') is not None
cpp_skip = pytest.mark.skipif(not has_cpp, reason='g++ not available')


@cpp_skip
class TestCppCorrect:
    def test_cpp_all_pass(self, app, task_with_tests):
        code = '''#include <iostream>
using namespace std;
int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}
'''
        with app.app_context():
            result = check_submission(code, 'cpp', task_with_tests)
        assert result['status'] == 'ok'
        assert result['passed'] == 3


@cpp_skip
class TestCppCompileError:
    def test_compile_error(self, app, task_with_tests):
        code = '''#include <iostream>
int main() {
    cout << "hello"  // missing semicolon
    return 0;
}
'''
        with app.app_context():
            result = check_submission(code, 'cpp', task_with_tests)
        assert result['status'] == 'error'
        assert result['compile_error'] is not None
        assert len(result['compile_error']) > 0


@cpp_skip
class TestCppWrongAnswer:
    def test_cpp_wrong_answer(self, app, task_with_tests):
        code = '''#include <iostream>
using namespace std;
int main() {
    int a, b;
    cin >> a >> b;
    cout << a * b << endl;
    return 0;
}
'''
        with app.app_context():
            result = check_submission(code, 'cpp', task_with_tests)
        assert result['status'] == 'error'
        assert result['passed'] == 0


# ── Edge cases ─────────────────────────────────────────────────────────


class TestResultStructure:
    def test_result_has_required_keys(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a + b)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        assert 'status' in result
        assert 'total_tests' in result
        assert 'passed' in result
        assert 'results' in result
        assert 'compile_error' in result

    def test_each_result_has_number_status_message(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a + b)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        for r in result['results']:
            assert 'number' in r
            assert 'status' in r
            assert 'message' in r

    def test_results_sorted_by_number(self, app, task_with_tests):
        code = 'a, b = map(int, input().split())\nprint(a + b)\n'
        with app.app_context():
            result = check_submission(code, 'python', task_with_tests)
        nums = [r['number'] for r in result['results']]
        assert nums == sorted(nums)


class TestUnsupportedLanguage:
    def test_unsupported_language(self, app, task_with_tests):
        with app.app_context():
            result = check_submission('x = 1', 'java', task_with_tests)
        assert result['status'] == 'error'
        assert result['compile_error'] is not None
