"""Разбор тестового файла графа."""

import unittest

from src.errors import DataError
from src.test_repo import parse_test_repo


class RepoTest(unittest.TestCase):
    """Имена в файле — большие латинские буквы."""

    def test_chain(self):
        """Первое слово — пакет, остальные — зависимости."""
        graph = parse_test_repo('A B\nB C\nC\n')
        self.assertEqual(graph['A'], ['B'])
        self.assertEqual(graph['B'], ['C'])
        self.assertEqual(graph['C'], [])

    def test_leaf_without_line(self):
        """Имя только в зависимостях тоже становится пакетом."""
        graph = parse_test_repo('A B\n')
        self.assertEqual(graph['B'], [])

    def test_bad_name(self):
        """Строчные буквы в тестовом файле запрещены."""
        with self.assertRaises(DataError):
            parse_test_repo('A b\n')

    def test_duplicate(self):
        """Один пакет нельзя описать два раза."""
        with self.assertRaises(DataError):
            parse_test_repo('A B\nA C\n')


if __name__ == '__main__':
    unittest.main()
