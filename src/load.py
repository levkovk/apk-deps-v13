"""Откуда брать таблицу прямых зависимостей."""

from src.apk_index import load_index
from src.errors import DataError
from src.test_repo import load_test_repo


def load_forward(config):
    """Имя пакета -> прямые зависимости."""
    if config.test:
        return _from_test(config)
    return _from_apk(config)


def _from_test(config):
    """Граф из тестового файла."""
    graph = load_test_repo(config.repo)
    if config.package not in graph:
        raise DataError(f'пакет {config.package} не найден')
    return graph


def _from_apk(config):
    """Граф из индекса Alpine для выбранной версии."""
    index = load_index(config.repo)
    selected = index.require(config.package, config.version)
    return index.forward(selected)
