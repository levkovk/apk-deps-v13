"""Проверка сравнения версий Alpine."""

import unittest

from src.apk_version import (
    EQUAL,
    GREATER,
    LESS,
    compare,
    is_valid_version,
    version_matches,
)


class VersionTest(unittest.TestCase):
    """Правила сравнения взяты из apk-tools."""

    def test_equal(self):
        """Одинаковые номера равны."""
        self.assertEqual(compare('1.2.5-r12', '1.2.5-r12'), EQUAL)

    def test_numeric(self):
        """1.10 больше 1.9, сравнение чисел, а не строк."""
        self.assertEqual(compare('1.10', '1.9'), GREATER)
        self.assertEqual(compare('2.0', '1.9'), GREATER)

    def test_prerelease_order(self):
        """alpha < beta < pre < rc < обычная версия."""
        order = (
            '1.0_alpha',
            '1.0_beta',
            '1.0_pre',
            '1.0_rc',
            '1.0',
        )
        for left, right in zip(order, order[1:]):
            self.assertEqual(compare(left, right), LESS)

    def test_revision(self):
        """Ревизия -r увеличивает версию."""
        self.assertEqual(compare('1.0', '1.0-r0'), LESS)
        self.assertEqual(compare('1.0-r0', '1.0-r1'), LESS)

    def test_leading_zero(self):
        """Первое число без ведущего нуля, следующее — как строка."""
        self.assertEqual(compare('01', '1'), EQUAL)
        self.assertEqual(compare('1.01', '1.1'), LESS)

    def test_patch_suffix(self):
        """Суффикс _p больше версии без суффикса."""
        self.assertEqual(compare('1.0_p1', '1.0'), GREATER)

    def test_fuzzy(self):
        """Оператор ~ принимает продолжение номера."""
        self.assertTrue(version_matches('3.12.6', '~', '3.12'))
        self.assertFalse(version_matches('3.13.0', '~', '3.12'))

    def test_operators(self):
        """Обычные операторы =, >= и >."""
        self.assertTrue(version_matches('1.2.5-r12', '=', '1.2.5-r12'))
        self.assertTrue(version_matches('1.2.5-r12', '>=', '1.2.0'))
        self.assertFalse(version_matches('1.0', '>', '1.0'))
        self.assertTrue(version_matches('1.0', '', ''))

    def test_valid(self):
        """Пустая строка и слово — не версии."""
        self.assertTrue(is_valid_version('1.2.5-r12'))
        self.assertFalse(is_valid_version(''))
        self.assertFalse(is_valid_version('abc'))
        self.assertFalse(is_valid_version('1.0__nope'))


if __name__ == '__main__':
    unittest.main()
