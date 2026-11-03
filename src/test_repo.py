"""Файл тестового графа. Имена — большие латинские буквы."""

import re
from pathlib import Path

from src.errors import DataError

_NAME = re.compile(r'^[A-Z]+$')


def load_test_repo(path):
    """Прочитать граф из файла."""
    text = Path(path).read_text(encoding='utf-8')
    return parse_test_repo(text)


def parse_test_repo(text):
    """Разобрать строки «ИМЯ ЗАВИСИМОСТЬ ЗАВИСИМОСТЬ»."""
    graph = {}
    for line in text.splitlines():
        _add_line(graph, line)
    _add_leaves(graph)
    return graph


def _add_line(graph, line):
    """Добавить одну строку файла в граф."""
    parts = line.split()
    if not parts:
        return
    _check_names(parts)
    name = parts[0]
    if name in graph:
        raise DataError(f'пакет {name} указан дважды')
    graph[name] = parts[1:]


def _check_names(parts):
    """Каждое имя состоит только из больших латинских букв."""
    for name in parts:
        if _NAME.fullmatch(name) is None:
            raise DataError(
                f'имя {name} не из больших латинских букв',
            )


def _add_leaves(graph):
    """Зависимость без своей строки — пакет без зависимостей."""
    missing = []
    for deps in list(graph.values()):
        for dep in deps:
            if dep not in graph:
                missing.append(dep)
    for name in missing:
        graph[name] = []
