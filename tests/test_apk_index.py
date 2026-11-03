"""Разбор индекса Alpine без сети."""

import io
import tarfile
import unittest

from src.apk_index import direct_text, parse_index, parse_tar_gz
from src.errors import DataError

SAMPLE = """
C:Q1aaa
P:musl
V:1.2.5-r12
p:so:libc.musl-x86_64.so.1=1

C:Q1bbb
P:zlib
V:1.3.2-r1
D:so:libc.musl-x86_64.so.1
p:so:libz.so.1=1.3.2

C:Q1ccc
P:busybox
V:1.37.0-r14
D:so:libc.musl-x86_64.so.1 !other
k:100
""".strip()


class IndexTest(unittest.TestCase):
    """Прямые зависимости читаются из текста APKINDEX."""

    def test_direct_deps_of_zlib(self):
        """Поле D печатается по одному токену в строке."""
        index = parse_index(SAMPLE)
        package = index.require('zlib', '1.3.2-r1')
        self.assertEqual(
            direct_text(package),
            'so:libc.musl-x86_64.so.1',
        )

    def test_musl_has_no_deps(self):
        """Пустое поле D — это не ошибка."""
        index = parse_index(SAMPLE)
        package = index.require('musl', '1.2.5-r12')
        self.assertEqual(direct_text(package), 'зависимостей нет')

    def test_conflict_is_skipped(self):
        """Запись !пакет — конфликт, не зависимость."""
        index = parse_index(SAMPLE)
        package = index.require('busybox', '1.37.0-r14')
        self.assertEqual(
            direct_text(package),
            'so:libc.musl-x86_64.so.1',
        )
        self.assertEqual(package.priority, 100)

    def test_missing_package(self):
        """Неизвестное имя дает ошибку."""
        index = parse_index(SAMPLE)
        with self.assertRaises(DataError):
            index.require('nope', '1.0')

    def test_missing_version(self):
        """Имя есть, а такой версии нет."""
        index = parse_index(SAMPLE)
        with self.assertRaises(DataError):
            index.require('zlib', '9.9.9')

    def test_empty_index(self):
        """Индекс без пакетов читать нельзя."""
        with self.assertRaises(DataError):
            parse_index('T:только описание\n')

    def test_tar_gz(self):
        """APKINDEX.tar.gz раскрывается до тех же пакетов."""
        data = _tar_gz({'APKINDEX': SAMPLE + '\n'})
        index = parse_tar_gz(data)
        package = index.require('musl', '1.2.5-r12')
        self.assertEqual(package.provides[0][0], 'so:libc.musl-x86_64.so.1')


def _tar_gz(files):
    """Собрать gzip-архив tar в памяти."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as archive:
        for name, text in files.items():
            payload = text.encode('utf-8')
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


if __name__ == '__main__':
    unittest.main()
