"""Чтение индекса пакетов Alpine APKINDEX."""

import io
import tarfile
import urllib.error
import urllib.request

from src.apk_version import GREATER, compare, version_matches
from src.errors import DataError

ZERO = 0
TIMEOUT_SEC = 60
DEFAULT_PRIORITY = 0
INDEX_NAME = 'APKINDEX.tar.gz'
_OPS = ('>=', '<=', '>~', '<~', '=', '~', '>', '<')


class Package:
    """Один пакет из APKINDEX."""

    def __init__(self, name, version, depends, provides, priority):
        """Сохранить поля пакета, нужные для графа."""
        self.name = name
        self.version = version
        self.depends = depends
        self.provides = provides
        self.priority = priority


class Index:
    """Пакеты одного репозитория."""

    def __init__(self, packages):
        """Разложить пакеты по имени и по provides."""
        self.packages = packages
        self.by_name = {}
        self.by_provide = {}
        for package in packages:
            self._add(package)

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

    def forward(self, selected):
        """Имя пакета и список имен его прямых зависимостей."""
        chosen = {}
        for name, packages in self.by_name.items():
            chosen[name] = _newest(packages)
        chosen[selected.name] = selected
        result = {}
        for name, package in chosen.items():
            result[name] = self.dep_names(package)
        return result

    def dep_names(self, package):
        """Имена пакетов, от которых зависит package."""
        names = []
        for token in package.depends:
            resolved = self.resolve(token)
            if resolved is None:
                continue
            names.append(resolved)
        return names

    def resolve(self, token):
        """Имя пакета для токена зависимости. None — это конфликт."""
        conflict, name, operator, required = split_dep(token)
        if conflict or name == '':
            return None
        own = self._match_name(name, operator, required)
        if own is not None:
            return own.name
        provided = self._match_provide(name, operator, required)
        if provided is not None:
            return provided.name
        if operator == '':
            return name
        return token

    def _match_name(self, name, operator, required):
        """Пакет с таким именем, если версия подходит."""
        matched = []
        for package in self.by_name.get(name, []):
            if version_matches(package.version, operator, required):
                matched.append(package)
        return _newest(matched)

    def _match_provide(self, name, operator, required):
        """Пакет, который предоставляет имя. Берется больший приоритет."""
        matched = []
        for package, provided_ver in self.by_provide.get(name, []):
            ver = provided_ver or package.version
            if version_matches(ver, operator, required):
                matched.append(package)
        return _highest_priority(matched)

    def forward(self, selected):
        """Имя пакета -> имена его прямых зависимостей."""
        chosen = self._one_per_name()
        chosen[selected.name] = selected
        result = {}
        for name, package in chosen.items():
            result[name] = self.dep_names(package)
        return result

    def dep_names(self, package):
        """Имена пакетов для прямых зависимостей package."""
        names = []
        for token in package.depends:
            resolved = self.resolve(token)
            if resolved is None:
                continue
            names.append(resolved)
        return names

    def resolve(self, token):
        """Имя пакета для токена зависимости. None — это конфликт."""
        conflict, name, operator, required = split_dep(token)
        if conflict or name == '':
            return None
        own = self._own(name, operator, required)
        if own is not None:
            return own.name
        provided = self._provided(name, operator, required)
        if provided is not None:
            return provided.name
        return _unresolved(name, operator, token)

    def _add(self, package):
        """Добавить пакет в оба указателя."""
        names = self.by_name.setdefault(package.name, [])
        names.append(package)
        for provided, provided_ver in package.provides:
            bucket = self.by_provide.setdefault(provided, [])
            bucket.append((package, provided_ver))

    def _one_per_name(self):
        """По одному пакету на имя: берется самая новая версия."""
        chosen = {}
        for name, packages in self.by_name.items():
            chosen[name] = _newest(packages)
        return chosen

    def _own(self, name, operator, required):
        """Пакет с таким именем, если версия подходит."""
        matched = []
        for package in self.by_name.get(name, []):
            if version_matches(package.version, operator, required):
                matched.append(package)
        if not matched:
            return None
        return _newest(matched)

    def _provided(self, name, operator, required):
        """Пакет, который предоставляет имя, с наибольшим приоритетом."""
        matched = []
        for package, provided_ver in self.by_provide.get(name, []):
            ver = provided_ver or package.version
            if version_matches(ver, operator, required):
                matched.append(package)
        if not matched:
            return None
        return _highest_priority(matched)


def load_package(repo, name, version):
    """Скачать индекс и вернуть нужный пакет."""
    index = load_index(repo)
    return index.require(name, version)


def load_index(repo):
    """Скачать APKINDEX.tar.gz и разобрать его."""
    url = index_url(repo)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEC) as resp:
            data = resp.read()
    except urllib.error.URLError as err:
        reason = getattr(err, 'reason', err)
        raise DataError(f'не удалось скачать индекс: {reason}') from err
    return parse_tar_gz(data)


def index_url(repo):
    """Адрес APKINDEX.tar.gz для URL репозитория."""
    base = repo.rstrip('/')
    if base.endswith(INDEX_NAME):
        return base
    return f'{base}/{INDEX_NAME}'


def parse_tar_gz(data):
    """Разобрать скачанный APKINDEX.tar.gz."""
    try:
        archive = tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')
    except tarfile.TarError as err:
        raise DataError('файл индекса поврежден') from err
    with archive:
        text = _index_text(archive)
    return parse_index(text)


def split_dep(token):
    """Разобрать токен на конфликт, имя, оператор и версию."""
    body = token
    conflict = body.startswith('!')
    if conflict:
        body = body[1:]
    op, pos = _find_op(body)
    if op == '':
        return conflict, body, '', ''
    return conflict, body[:pos], op, body[pos + len(op):]


def _find_op(body):
    """Самый левый оператор версии в токене."""
    best = None
    for op in _OPS:
        best = _closer(best, body.find(op), op)
    if best is None:
        return '', ZERO
    return best[1], best[0]


def _closer(best, pos, op):
    """Оставить оператор, который стоит левее."""
    if pos < ZERO:
        return best
    if best is None or pos < best[0]:
        return (pos, op)
    return best


def _newest(packages):
    """Пакет с самой большой версией или None."""
    if not packages:
        return None
    best = packages[0]
    for package in packages[1:]:
        if compare(package.version, best.version) == GREATER:
            best = package
    return best


def _highest_priority(packages):
    """Провайдер с наибольшим полем k."""
    if not packages:
        return None
    best = packages[0]
    for package in packages[1:]:
        if _prefer(package, best):
            best = package
    return best


def _prefer(left, right):
    """True, если left лучше right по приоритету, затем по версии."""
    if left.priority != right.priority:
        return left.priority > right.priority
    return compare(left.version, right.version) == GREATER


def parse_index(text):
    """Разобрать текст файла APKINDEX."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    packages = []
    for block in text.split('\n\n'):
        package = _parse_block(block)
        if package is not None:
            packages.append(package)
    if not packages:
        raise DataError('индекс не содержит пакетов')
    return Index(packages)


def direct_text(package):
    """Прямые зависимости так, как они записаны в индексе."""
    lines = _depend_lines(package)
    if not lines:
        return 'зависимостей нет'
    return '\n'.join(lines)


def split_dep(token):
    """Разделить токен на конфликт, имя, оператор и версию."""
    body = token
    conflict = False
    if body.startswith('!'):
        conflict = True
        body = body[1:]
    operator, pos = _find_op(body)
    if operator == '':
        return conflict, body, '', ''
    name = body[:pos]
    version = body[pos + len(operator):]
    return conflict, name, operator, version


def _index_text(archive):
    """Достать файл APKINDEX из архива."""
    try:
        member = archive.extractfile('APKINDEX')
    except KeyError as err:
        raise DataError('в архиве нет файла APKINDEX') from err
    if member is None:
        raise DataError('в архиве нет файла APKINDEX')
    return member.read().decode('utf-8')


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
    """Словарь полей блока. Ключ — буква до двоеточия."""
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
        _conflict, name, _operator, version = split_dep(token)
        if name == '':
            continue
        items.append((name, version))
    return items


def _priority(text):
    """Число из поля k. Пустое поле значит приоритет по умолчанию."""
    if text == '':
        return DEFAULT_PRIORITY
    return int(text)


def _depend_lines(package):
    """Токены зависимостей без конфликтов, помеченных !."""
    lines = []
    for token in package.depends:
        if token.startswith('!'):
            continue
        lines.append(token)
    return lines


def _find_op(body):
    """Самый левый оператор версии в токене."""
    best = None
    for operator in _OPS:
        pos = body.find(operator)
        best = _closer(best, pos, operator)
    if best is None:
        return '', ZERO
    return best[1], best[0]


def _closer(best, pos, operator):
    """Оставить оператор, который стоит левее."""
    if pos < ZERO:
        return best
    if best is None or pos < best[0]:
        return (pos, operator)
    return best


def _unresolved(name, operator, token):
    """Имя листа, если подходящий пакет не найден."""
    if operator == '':
        return name
    return token


def _newest(packages):
    """Пакет с самой большой версией."""
    best = packages[0]
    for package in packages[1:]:
        if compare(package.version, best.version) == GREATER:
            best = package
    return best


def _highest_priority(packages):
    """Пакет с наибольшим приоритетом provides."""
    best = packages[0]
    for package in packages[1:]:
        if _prefer(package, best):
            best = package
    return best


def _prefer(left, right):
    """True, если left лучше right по приоритету, затем по версии."""
    if left.priority != right.priority:
        return left.priority > right.priority
    return compare(left.version, right.version) == GREATER
