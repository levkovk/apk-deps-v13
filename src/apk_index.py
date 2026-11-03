"""Чтение индекса пакетов Alpine APKINDEX."""

import io
import tarfile
import urllib.error
import urllib.request

from src.errors import DataError

TIMEOUT_SEC = 60
DEFAULT_PRIORITY = 0
INDEX_NAME = 'APKINDEX.tar.gz'


class Package:
    """Один пакет из APKINDEX."""

    def __init__(self, name, version, depends, provides, priority):
        """Сохранить поля пакета, нужные для зависимостей."""
        self.name = name
        self.version = version
        self.depends = depends
        self.provides = provides
        self.priority = priority


class Index:
    """Все пакеты одного репозитория."""

    def __init__(self, packages):
        """Сложить пакеты по имени."""
        self.packages = packages
        self.by_name = {}
        for package in packages:
            self._add(package)

    def _add(self, package):
        """Добавить пакет в указатель по имени."""
        bucket = self.by_name.setdefault(package.name, [])
        bucket.append(package)

    def require(self, name, version):
        """Найти пакет с точным именем и версией."""
        found = self.by_name.get(name, [])
        for package in found:
            if package.version == version:
                return package
        if not found:
            raise DataError(f'пакет {name} не найден')
        raise DataError(
            f'версия {version} пакета {name} не найдена',
        )


def direct_text(package):
    """Прямые зависимости так, как они записаны в индексе."""
    lines = _plain_deps(package)
    if not lines:
        return 'зависимостей нет'
    return '\n'.join(lines)


def _plain_deps(package):
    """Токены поля D без конфликтов, помеченных знаком !."""
    lines = []
    for token in package.depends:
        if token.startswith('!'):
            continue
        lines.append(token)
    return lines


def load_package(repo, name, version):
    """Скачать индекс и вернуть один пакет."""
    return load_index(repo).require(name, version)


def load_index(repo):
    """Скачать APKINDEX.tar.gz и разобрать его."""
    data = _download(index_url(repo))
    return parse_tar_gz(data)


def index_url(repo):
    """Адрес файла APKINDEX.tar.gz."""
    base = repo.rstrip('/')
    if base.endswith(INDEX_NAME):
        return base
    return f'{base}/{INDEX_NAME}'


def _download(url):
    """Скачать адрес и вернуть байты."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEC) as resp:
            return resp.read()
    except urllib.error.URLError as err:
        reason = getattr(err, 'reason', err)
        raise DataError(
            f'не удалось скачать индекс: {reason}',
        ) from err


def parse_tar_gz(data):
    """Разобрать скачанный APKINDEX.tar.gz."""
    try:
        archive = tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')
    except tarfile.TarError as err:
        raise DataError('файл индекса поврежден') from err
    with archive:
        text = _index_text(archive)
    return parse_index(text)


def _index_text(archive):
    """Достать из архива текст файла APKINDEX."""
    try:
        member = archive.extractfile('APKINDEX')
    except KeyError as err:
        raise DataError('в архиве нет файла APKINDEX') from err
    if member is None:
        raise DataError('в архиве нет файла APKINDEX')
    return member.read().decode('utf-8')


def parse_index(text):
    """Разобрать текст файла APKINDEX."""
    packages = []
    for block in text.split('\n\n'):
        package = _parse_block(block)
        if package is not None:
            packages.append(package)
    if not packages:
        raise DataError('индекс не содержит пакетов')
    return Index(packages)


def _parse_block(block):
    """Собрать пакет из одного блока индекса."""
    fields = _fields(block)
    name = fields.get('P', '')
    version = fields.get('V', '')
    if name == '' or version == '':
        return None
    depends = fields.get('D', '').split()
    provides = _provides(fields.get('p', ''))
    priority = _priority(fields.get('k', ''))
    return Package(name, version, depends, provides, priority)


def _fields(block):
    """Разобрать строки вида ключ:значение."""
    fields = {}
    for line in block.splitlines():
        key, value = _pair(line)
        if key == '':
            continue
        fields[key] = value
    return fields


def _pair(line):
    """Разделить строку на ключ и значение."""
    key, sep, value = line.partition(':')
    if sep == '':
        return '', ''
    return key, value


def _provides(text):
    """Список пар (имя, версия) из поля p."""
    items = []
    for token in text.split():
        name, sep, version = token.partition('=')
        if name == '':
            continue
        if sep == '':
            version = ''
        items.append((name, version))
    return items


def _priority(text):
    """Число из поля k. Если поля нет, приоритет нулевой."""
    if text == '':
        return DEFAULT_PRIORITY
    return int(text)
