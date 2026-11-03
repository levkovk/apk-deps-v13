"""Точка входа командной строки."""

import sys

from src.apk_index import direct_text, load_package
from src.config import ConfigError, parse_args
from src.errors import DataError

EXIT_OK = 0
EXIT_FAIL = 1


def main(argv=None):
    """Запустить программу и вернуть код выхода."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        config = parse_args(argv)
        package = _load(config)
    except (ConfigError, DataError) as err:
        print(f'ошибка: {err}', file=sys.stderr)
        return EXIT_FAIL
    print(direct_text(package))
    return EXIT_OK


def _load(config):
    """Прочитать пакет из репозитория Alpine."""
    if config.test:
        raise DataError(
            'для зависимостей нужен URL репозитория, без --test',
        )
    return load_package(config.repo, config.package, config.version)


if __name__ == '__main__':
    sys.exit(main())
