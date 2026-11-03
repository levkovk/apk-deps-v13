"""Обход графа, фильтр и циклы."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.graph import bfs_graph, format_graph, format_reverse
from src.main import main

DATA = Path(__file__).resolve().parent / 'data'


def _run(argv):
    """Запустить main и вернуть код и stdout."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue().strip(), err.getvalue()


class GraphTest(unittest.TestCase):
    """BFS на тестовых файлах."""

    def test_chain(self):
        """Цепочка A -> B -> C."""
        code, out, err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'chain.txt'),
            '--test',
        ])
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        self.assertEqual(
            out,
            '@startuml\n"A" --> "B"\n"B" --> "C"\n@enduml',
        )

    def test_branch(self):
        """Ромб не является циклом."""
        code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'branch.txt'),
            '--test',
        ])
        self.assertEqual(code, 0)
        self.assertIn('"A" --> "B"', out)
        self.assertIn('"C" --> "D"', out)
        self.assertNotIn('цикл', out)

    def test_cycle(self):
        """Цикл обходится один раз и помечается."""
        _code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'cycle.txt'),
            '--test',
        ])
        self.assertIn('"A" --> "B"', out)
        self.assertIn('"C" --> "A"', out)
        self.assertTrue(out.startswith('@startuml'))

    def test_filter(self):
        """Пакет с подстрокой фильтра не попадает в граф."""
        _code, out, _err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'branch.txt'),
            '--test',
            '--filter', 'D',
        ])
        self.assertIn('"A" --> "B"', out)
        self.assertIn('"A" --> "C"', out)
        self.assertNotIn('D', out)

    def test_filter_root(self):
        """Если фильтр отсекает сам пакет, граф пустой."""
        graph = bfs_graph('A', {'A': ['B']}, 'A')
        self.assertEqual(format_graph(graph), 'пакет исключен фильтром')

    def test_no_deps(self):
        """У пакета C в цепочке зависимостей нет."""
        _code, out, _err = _run([
            '--package', 'C',
            '--repo', str(DATA / 'chain.txt'),
            '--test',
        ])
        self.assertEqual(out, '@startuml\n"C"\n@enduml')

    def test_reverse(self):
        """От A зависят B и C напрямую и D через B."""
        code, out, err = _run([
            '--package', 'A',
            '--repo', str(DATA / 'reverse.txt'),
            '--test',
            '--reverse',
        ])
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        self.assertEqual(out, 'B\nC\nD')

    def test_reverse_direct(self):
        """format_reverse вызывает обход по развернутым ребрам."""
        forward = {'A': [], 'B': ['A'], 'C': ['B']}
        self.assertEqual(format_reverse('B', forward, ''), 'C')

    def test_missing_package(self):
        """В файле нет такого пакета."""
        code, _out, err = _run([
            '--package', 'Z',
            '--repo', str(DATA / 'chain.txt'),
            '--test',
        ])
        self.assertEqual(code, 1)
        self.assertIn('не найден', err)


if __name__ == '__main__':
    unittest.main()
