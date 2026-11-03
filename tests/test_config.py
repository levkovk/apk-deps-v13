"""Проверка параметров командной строки."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.config import ConfigError, format_config, parse_args
from src.main import main


def _run(argv):
    """Запустить main и вернуть код, stdout и stderr."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class ConfigTest(unittest.TestCase):
    """Ошибки и нормальные значения всех параметров."""

    def test_prints_pairs(self):
        """Проверенные параметры собираются в пары ключ=значение."""
        config = parse_args([
            '--package', 'musl',
            '--repo', 'https://example.com/alpine',
            '--version', '1.2.5-r12',
            '--filter', 'doc',
        ])
        text = format_config(config)
        self.assertIn('package=musl', text)
        self.assertIn('repo=https://example.com/alpine', text)
        self.assertIn('test=false', text)
        self.assertIn('version=1.2.5-r12', text)
        self.assertIn('filter=doc', text)

    def test_format_matches_fields(self):
        """format_config собирает те же пять строк."""
        config = parse_args([
            '--package', 'zlib',
            '--repo', 'https://example.com/alpine',
            '--version', '1.3.2-r1',
        ])
        text = format_config(config)
        self.assertEqual(text.splitlines()[0], 'package=zlib')
        self.assertIn('filter=', text)

    def test_missing_package(self):
        """Без имени пакета программа пишет ошибку."""
        code, _out, err = _run([
            '--repo', 'https://example.com/alpine',
            '--version', '1.0',
        ])
        self.assertEqual(code, 1)
        self.assertIn('не задано имя пакета', err)

    def test_bad_package(self):
        """Имя пакета Alpine пишется строчными буквами."""
        with self.assertRaises(ConfigError):
            parse_args([
                '--package', 'Musl',
                '--repo', 'https://example.com/alpine',
                '--version', '1.0',
            ])

    def test_missing_repo(self):
        """Без репозитория программа пишет ошибку."""
        code, _out, err = _run([
            '--package', 'musl',
            '--version', '1.0',
        ])
        self.assertEqual(code, 1)
        self.assertIn('не задан репозиторий', err)

    def test_repo_not_url(self):
        """В обычном режиме репозиторий — это http или https."""
        with self.assertRaises(ConfigError):
            parse_args([
                '--package', 'musl',
                '--repo', 'ftp://example.com/alpine',
                '--version', '1.0',
            ])

    def test_missing_version(self):
        """Без версии программа пишет ошибку."""
        code, _out, err = _run([
            '--package', 'musl',
            '--repo', 'https://example.com/alpine',
        ])
        self.assertEqual(code, 1)
        self.assertIn('не задана версия пакета', err)

    def test_bad_version(self):
        """Пробел в версии не допускается."""
        with self.assertRaises(ConfigError):
            parse_args([
                '--package', 'musl',
                '--repo', 'https://example.com/alpine',
                '--version', '1.0 r1',
            ])

    def test_blank_filter(self):
        """Фильтр из одних пробелов — ошибка."""
        with self.assertRaises(ConfigError):
            parse_args([
                '--package', 'musl',
                '--repo', 'https://example.com/alpine',
                '--version', '1.0',
                '--filter', '   ',
            ])

    def test_test_mode_file(self):
        """В тестовом режиме нужен существующий файл и имя из букв."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'repo.txt'
            path.write_text('A B\n', encoding='utf-8')
            config = parse_args([
                '--package', 'A',
                '--repo', str(path),
                '--test',
            ])
        self.assertTrue(config.test)
        self.assertEqual(config.version, '')
        self.assertEqual(config.package, 'A')

    def test_test_mode_rejects_url(self):
        """В тестовом режиме URL вместо файла — ошибка."""
        with self.assertRaises(ConfigError):
            parse_args([
                '--package', 'A',
                '--repo', 'https://example.com/alpine',
                '--test',
            ])

    def test_test_mode_missing_file(self):
        """Если тестового файла нет, это ошибка."""
        with self.assertRaises(ConfigError):
            parse_args([
                '--package', 'A',
                '--repo', 'no-such-file.txt',
                '--test',
            ])

    def test_test_mode_bad_name(self):
        """Строчное имя в тестовом режиме не принимается."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'repo.txt'
            path.write_text('A\n', encoding='utf-8')
            with self.assertRaises(ConfigError):
                parse_args([
                    '--package', 'musl',
                    '--repo', str(path),
                    '--test',
                ])


if __name__ == '__main__':
    unittest.main()
