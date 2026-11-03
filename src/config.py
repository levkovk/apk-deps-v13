"""Параметры командной строки."""

import argparse
import re
from pathlib import Path


class ConfigError(Exception):
    """Параметр командной строки задан неверно."""


class Config:
    """Настройки одного запуска."""

    def __init__(
        self, package, repo, test, version, filter_text, reverse,
    ):
        """Запомнить уже проверенные параметры."""
        self.package = package
        self.repo = repo
        self.test = test
        self.version = version
        self.filter_text = filter_text
        self.reverse = reverse


_REAL_NAME = re.compile(r'^[a-z0-9][a-z0-9+_.-]*$')
_TEST_NAME = re.compile(r'^[A-Z]+$')
_VERSION = re.compile(r'^[0-9A-Za-z._+~-]+$')


def parse_args(argv):
    """Разобрать argv и вернуть Config либо выбросить ConfigError."""
    parser = _parser()
    args = parser.parse_args(argv)
    return _build(args)


def format_config(config):
    """Текст ключ=значение со всеми параметрами."""
    flag = 'true' if config.test else 'false'
    version = config.version or ''
    lines = (
        f'package={config.package}',
        f'repo={config.repo}',
        f'test={flag}',
        f'version={version}',
        f'filter={config.filter_text}',
    )
    return '\n'.join(lines)


def _parser():
    """Описание опций командной строки."""
    parser = argparse.ArgumentParser(
        prog='deps',
        description='Граф зависимостей пакетов Alpine apk.',
    )
    parser.add_argument('--package', help='Имя пакета')
    parser.add_argument(
        '--repo',
        help='URL репозитория или путь к тестовому файлу',
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Читать тестовый файл графа, а не репозиторий',
    )
    parser.add_argument('--version', help='Версия пакета')
    parser.add_argument(
        '--filter',
        default='',
        help='Не учитывать пакеты с этой подстрокой в имени',
    )
    parser.add_argument(
        '--reverse',
        action='store_true',
        help='Показать пакеты, которые зависят от заданного',
    )
    return parser


def _build(args):
    """Собрать Config после проверки каждого параметра."""
    package = _package(args.package, args.test)
    repo = _repo(args.repo, args.test)
    version = _version(args.version, args.test)
    filter_text = _filter(args.filter)
    return Config(
        package, repo, args.test, version, filter_text, args.reverse,
    )


def _package(value, test):
    """Проверить имя пакета."""
    if value is None or value.strip() == '':
        raise ConfigError('не задано имя пакета')
    name = value.strip()
    if test:
        return _test_package(name)
    if _REAL_NAME.fullmatch(name) is None:
        raise ConfigError('неверное имя пакета')
    return name


def _test_package(name):
    """В тестовом файле пакет называется большими латинскими буквами."""
    if _TEST_NAME.fullmatch(name) is None:
        raise ConfigError(
            'в тесте имя пакета — большие латинские буквы',
        )
    return name


def _repo(value, test):
    """Проверить адрес репозитория или путь к тестовому файлу."""
    if value is None or value.strip() == '':
        raise ConfigError('не задан репозиторий')
    repo = value.strip()
    if test:
        return _test_repo(repo)
    return _remote_repo(repo)


def _test_repo(repo):
    """Путь к файлу тестового графа."""
    if _is_url(repo):
        raise ConfigError('в тестовом режиме нужен путь к файлу')
    if not Path(repo).is_file():
        raise ConfigError('файл тестового репозитория не найден')
    return repo


def _remote_repo(repo):
    """URL репозитория Alpine."""
    if not _is_url(repo):
        raise ConfigError(
            'адрес репозитория должен быть http или https',
        )
    return repo


def _is_url(repo):
    """True, если строка похожа на http(s)-адрес."""
    return repo.startswith('http://') or repo.startswith('https://')


def _version(value, test):
    """Проверить версию. В тестовом режиме ее можно не указывать."""
    if test:
        return _optional_version(value)
    if value is None or value.strip() == '':
        raise ConfigError('не задана версия пакета')
    return _check_version(value.strip())


def _optional_version(value):
    """Версия в тестовом режиме не обязательна."""
    if value is None or value.strip() == '':
        return ''
    return _check_version(value.strip())


def _check_version(version):
    """Версия без пробелов, в виде номера Alpine."""
    if _VERSION.fullmatch(version) is None:
        raise ConfigError('неверная версия пакета')
    return version


def _filter(value):
    """Подстрока фильтра. Пустая строка значит: не фильтровать."""
    if value is None:
        return ''
    if value.strip() == '' and value != '':
        raise ConfigError('пустая подстрока фильтра')
    return value
