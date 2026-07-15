import os
import re
import subprocess
import tempfile
import time

import psutil
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


def _tree_rss_kb(process):
    total = process.memory_info().rss
    for child in process.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return total / 1024


def _run_command(cmd, test_input, time_limit, memory_limit):
    no_input = test_input is None
    stdin = subprocess.DEVNULL if no_input else subprocess.PIPE
    proc = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p = psutil.Process(proc.pid)
    start = time.monotonic()

    try:
        stdout, stderr = proc.communicate(
            input=test_input if not no_input else None, timeout=0.1
        )
        return stdout, None, proc.returncode
    except subprocess.TimeoutExpired:
        pass

    error = None
    while True:
        if time.monotonic() - start > time_limit:
            error = 'time_limit'
            break
        if memory_limit:
            try:
                if _tree_rss_kb(p) > memory_limit:
                    error = 'memory_limit'
                    break
            except psutil.NoSuchProcess:
                pass
        try:
            stdout, stderr = proc.communicate(timeout=0.1)
            return stdout, error, proc.returncode
        except subprocess.TimeoutExpired:
            continue

    proc.kill()
    proc.communicate()
    return None, error, None


def _run_python(code, test_input, time_limit, memory_limit):
    python_exec = current_app.config.get('PYTHON_EXEC', 'python')
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as f:
        f.write(code)
        source_path = f.name

    try:
        return _run_command(
            [python_exec, source_path],
            test_input, time_limit, memory_limit,
        )
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


def _run_executable(exe_path, test_input, time_limit, memory_limit):
    return _run_command(
        [exe_path],
        test_input, time_limit, memory_limit,
    )


def check_submission(code, language, task_id):
    tests = get_tests(task_id)
    total = len(tests)
    results = []

    task = db.session.get(Task, task_id)
    time_limit = task.time_limit if task else \
        current_app.config.get('DEFAULT_TIME_LIMIT', 1)
    memory_limit = task.memory_limit if task else \
        current_app.config.get('DEFAULT_MEMORY_LIMIT', 256)

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
        if not test_input.strip():
            test_input = None
        if language == 'python':
            output, error, retcode = _run_python(code, test_input,
                                                  time_limit, memory_limit)
        else:
            output, error, retcode = _run_executable(
                exe_path, test_input, time_limit, memory_limit)

        if error == 'time_limit':
            results.append({
                'number': num,
                'status': 'time_limit',
                'message': 'Превышено ограничение времени',
            })
            continue

        if error == 'memory_limit':
            results.append({
                'number': num,
                'status': 'memory_limit',
                'message': 'Превышено ограничение памяти',
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
