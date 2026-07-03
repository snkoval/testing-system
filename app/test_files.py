import os
from pathlib import Path

from flask import current_app


def get_test_dir(task_id):
    base = current_app.config['TESTS_FOLDER']
    path = Path(base) / str(task_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _file_path(task_id, test_number, suffix):
    return get_test_dir(task_id) / f'{suffix}_{test_number}.txt'


def add_test(task_id, test_number, input_data, expected_output):
    in_path = _file_path(task_id, test_number, 'in')
    out_path = _file_path(task_id, test_number, 'out')
    in_path.write_text(input_data, encoding='utf-8')
    out_path.write_text(expected_output, encoding='utf-8')


def update_test(task_id, test_number, input_data, expected_output):
    add_test(task_id, test_number, input_data, expected_output)


def delete_test(task_id, test_number):
    in_path = _file_path(task_id, test_number, 'in')
    out_path = _file_path(task_id, test_number, 'out')
    if in_path.exists():
        in_path.unlink()
    if out_path.exists():
        out_path.unlink()


def get_tests(task_id):
    test_dir = get_test_dir(task_id)
    result = []
    for f in test_dir.glob('in_*.txt'):
        num = int(f.stem.split('_')[1])
        input_data = f.read_text(encoding='utf-8')
        out_file = test_dir / f'out_{num}.txt'
        expected = out_file.read_text(encoding='utf-8') if out_file.exists() else ''
        result.append((num, input_data, expected))
    result.sort(key=lambda x: x[0])
    return result


def get_test_count(task_id):
    return len(get_tests(task_id))


def get_examples(task_id):
    tests = get_tests(task_id)
    examples = []
    for i in range(min(2, len(tests))):
        num, inp, out = tests[i]
        examples.append((inp, out))
    return examples
