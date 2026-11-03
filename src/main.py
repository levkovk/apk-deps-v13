"""Точка входа командной строки."""

import sys

from src.config import ConfigError, format_config, parse_args

EXIT_OK = 0
EXIT_FAIL = 1


def main(argv=None):
    """Запустить программу и вернуть код выхода."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        config = parse_args(argv)
    except ConfigError as err:
        print(f'ошибка: {err}', file=sys.stderr)
        return EXIT_FAIL
    print(format_config(config))
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
