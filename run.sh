#!/bin/sh
cd "$(dirname "$0")" || exit 1
exec python -m src.main "$@"
