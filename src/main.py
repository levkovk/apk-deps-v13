"""Точка входа командной строки."""

import sys

from src.config import ConfigError, parse_args
from src.errors import DataError
from src.graph import bfs_graph, format_reverse, skipped
from src.load import load_forward
from src.plantuml import to_plantuml

EXIT_OK = 0
EXIT_FAIL = 1


def main(argv=None):
    """Запустить программу и вернуть код выхода."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        config = parse_args(argv)
        forward = load_forward(config)
    except (ConfigError, DataError) as err:
        print(f'ошибка: {err}', file=sys.stderr)
        return EXIT_FAIL
    print(_text(config, forward))
    return EXIT_OK


def _text(config, forward):
    """Диаграмма PlantUML или список обратных зависимостей."""
    if config.reverse:
        return format_reverse(
            config.package, forward, config.filter_text,
        )
    if skipped(config.package, config.filter_text):
        return 'пакет исключен фильтром'
    graph = bfs_graph(config.package, forward, config.filter_text)
    return to_plantuml(graph, config.package)


if __name__ == '__main__':
    sys.exit(main())
