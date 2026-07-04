import os
import re
import subprocess
import tempfile

from flask import current_app

from app import db
from app.models import Task
from app.test_files import get_tests


def _normalize_output(text):
    lines = text.splitlines()
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines)


def _run_python(code, test_input, time_limit):
    python_exec = current_app.config.get('PYTHON_EXEC', 'python')
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as f:
        f.write(code)
        source_path = f.name

    try:
        result = subprocess.run(
            [python_exec, source_path],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=time_limit,
        )
        return result.stdout, None, result.returncode
    except subprocess.TimeoutExpired:
        return None, 'time_limit', None
    finally:
        os.unlink(source_path)


def _compile_cpp(code):
    cpp_compiler = current_app.config.get('CPP_COMPILER', 'g++')
    upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                            os.path.join(tempfile.gettempdir(),
                                                         'uploads'))
    os.makedirs(upload_folder, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.cpp', delete=False, encoding='utf-8'
    ) as f:
        f.write(code)
        source_path = f.name

    exe_path = source_path.replace('.cpp', '.exe')
    try:
        result = subprocess.run(
            [cpp_compiler, '-o', exe_path, source_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None, result.stderr
        return exe_path, None
    except subprocess.TimeoutExpired:
        return None, 'Превышено время компиляции'
    except FileNotFoundError:
        return None, 'Компилятор не найден'


def _run_executable(exe_path, test_input, time_limit):
    try:
        result = subprocess.run(
            [exe_path],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=time_limit,
        )
        return result.stdout, None, result.returncode
    except subprocess.TimeoutExpired:
        return None, 'time_limit', None


def check_submission(code, language, task_id):
    tests = get_tests(task_id)
    total = len(tests)
    results = []

    task = db.session.get(Task, task_id)
    time_limit = task.time_limit if task else \
        current_app.config.get('DEFAULT_TIME_LIMIT', 1)

    if language not in ('python', 'cpp'):
        return {
            'status': 'error',
            'total_tests': total,
            'passed': 0,
            'results': [],
            'compile_error': 'Неподдерживаемый язык: ' + language,
        }

    exe_path = None
    if language == 'cpp':
        exe_path, compile_error = _compile_cpp(code)
        if compile_error:
            return {
                'status': 'error',
                'total_tests': total,
                'passed': 0,
                'results': [],
                'compile_error': compile_error,
            }

    passed_count = 0
    for num, test_input, expected in tests:
        if language == 'python':
            output, error, retcode = _run_python(code, test_input,
                                                  time_limit)
        else:
            output, error, retcode = _run_executable(
                exe_path, test_input, time_limit)

        if error == 'time_limit':
            results.append({
                'number': num,
                'status': 'time_limit',
                'message': 'Превышено ограничение времени',
            })
            continue

        if retcode != 0:
            results.append({
                'number': num,
                'status': 'runtime_error',
                'message': 'Ошибка выполнения',
            })
            continue

        if _normalize_output(output) == _normalize_output(expected):
            results.append({
                'number': num,
                'status': 'passed',
                'message': '',
            })
            passed_count += 1
        else:
            results.append({
                'number': num,
                'status': 'failed',
                'message': 'Неверный ответ',
            })

    if exe_path and os.path.exists(exe_path):
        os.unlink(exe_path)

    return {
        'status': 'ok' if passed_count == total else 'error',
        'total_tests': total,
        'passed': passed_count,
        'results': results,
        'compile_error': None,
    }
