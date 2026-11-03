"""Запуск на тестовых файлах."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.main import main

DATA = Path('tests') / 'data'


def _run(argv):
    """Запустить main и вернуть код и stdout."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class MainTest(unittest.TestCase):
    """Разные тестовые репозитории из задания."""

    def test_chain(self):
        """Цепочка зависимостей."""
        code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'chain.txt'),
            '--test',
        ])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), 'A -> B\nB -> C')

    def test_branch(self):
        """Ветвление без цикла."""
        code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'branch.txt'),
            '--test',
        ])
        self.assertEqual(code, 0)
        self.assertNotIn('цикл', out)
        self.assertIn('B -> D', out)

    def test_cycle(self):
        """Цикл A-B-C."""
        code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'cycle.txt'),
            '--test',
        ])
        self.assertEqual(code, 0)
        self.assertIn('цикл: A B C', out)

    def test_filter(self):
        """Фильтр убирает пакет D."""
        code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'branch.txt'),
            '--test',
            '--filter', 'D',
        ])
        self.assertEqual(code, 0)
        self.assertNotIn('D', out)

    def test_unknown(self):
        """Пакет, которого нет в файле."""
        code, _out, err = _run([
            '--package', 'Z',
            '--repo', str(DATA / 'chain.txt'),
            '--test',
        ])
        self.assertEqual(code, 1)
        self.assertIn('не найден', err)


if __name__ == '__main__':
    unittest.main()
