import os
import pytest

from app.test_files import (
    get_test_dir, get_tests, add_test, update_test,
    delete_test, get_examples, get_test_count
)


class TestGetTestDir:
    def test_returns_correct_path(self, app, tests_folder):
        with app.app_context():
            path = get_test_dir(42)
            assert str(path) == os.path.join(tests_folder, '42')

    def test_creates_dir_if_not_exists(self, app, tests_folder):
        with app.app_context():
            path = get_test_dir(1)
            assert os.path.isdir(path)


class TestAddTest:
    def test_add_test_creates_files(self, app, tests_folder):
        with app.app_context():
            add_test(1, 1, '5 3\n', '8\n')
            in_path = os.path.join(tests_folder, '1', 'in_1.txt')
            out_path = os.path.join(tests_folder, '1', 'out_1.txt')
            assert os.path.isfile(in_path)
            assert os.path.isfile(out_path)
            with open(in_path, encoding='utf-8') as f:
                assert f.read() == '5 3\n'
            with open(out_path, encoding='utf-8') as f:
                assert f.read() == '8\n'

    def test_add_multiple_tests(self, app, tests_folder):
        with app.app_context():
            add_test(1, 1, '1\n', '1\n')
            add_test(1, 2, '2\n', '4\n')
            assert os.path.isfile(os.path.join(tests_folder, '1', 'in_2.txt'))


class TestGetTests:
    def test_get_tests_empty(self, app):
        with app.app_context():
            tests = get_tests(999)
            assert tests == []

    def test_get_tests_returns_sorted(self, app):
        with app.app_context():
            add_test(1, 3, '3\n', '9\n')
            add_test(1, 1, '1\n', '1\n')
            add_test(1, 2, '2\n', '4\n')
            tests = get_tests(1)
            assert len(tests) == 3
            assert tests[0][0] == 1
            assert tests[1][0] == 2
            assert tests[2][0] == 3

    def test_get_tests_returns_content(self, app):
        with app.app_context():
            add_test(1, 1, '10\n', '100\n')
            tests = get_tests(1)
            assert len(tests) == 1
            num, inp, out = tests[0]
            assert num == 1
            assert inp == '10\n'
            assert out == '100\n'


class TestUpdateTest:
    def test_update_test(self, app, tests_folder):
        with app.app_context():
            add_test(1, 1, 'old\n', 'old_out\n')
            update_test(1, 1, 'new\n', 'new_out\n')
            with open(os.path.join(tests_folder, '1', 'in_1.txt'), encoding='utf-8') as f:
                assert f.read() == 'new\n'
            with open(os.path.join(tests_folder, '1', 'out_1.txt'), encoding='utf-8') as f:
                assert f.read() == 'new_out\n'


class TestDeleteTest:
    def test_delete_test(self, app, tests_folder):
        with app.app_context():
            add_test(1, 1, 'x\n', 'y\n')
            delete_test(1, 1)
            assert not os.path.isfile(os.path.join(tests_folder, '1', 'in_1.txt'))
            assert not os.path.isfile(os.path.join(tests_folder, '1', 'out_1.txt'))

    def test_delete_nonexistent_test(self, app):
        with app.app_context():
            delete_test(1, 99)


class TestGetExamples:
    def test_get_examples(self, app):
        with app.app_context():
            add_test(1, 1, 'input1\n', 'output1\n')
            add_test(1, 2, 'input2\n', 'output2\n')
            examples = get_examples(1)
            assert len(examples) == 2
            assert examples[0] == ('input1\n', 'output1\n')
            assert examples[1] == ('input2\n', 'output2\n')

    def test_get_examples_only_two(self, app):
        with app.app_context():
            add_test(1, 1, 'a\n', 'b\n')
            add_test(1, 2, 'c\n', 'd\n')
            add_test(1, 3, 'e\n', 'f\n')
            examples = get_examples(1)
            assert len(examples) == 2


class TestGetTestCount:
    def test_count_zero(self, app):
        with app.app_context():
            assert get_test_count(999) == 0

    def test_count_multiple(self, app):
        with app.app_context():
            add_test(1, 1, 'x\n', 'y\n')
            add_test(1, 2, 'x\n', 'y\n')
            add_test(1, 5, 'x\n', 'y\n')
            assert get_test_count(1) == 3
