"""Сравнение версий пакетов Alpine так, как это делает apk."""

ZERO = 0

TOKEN_INITIAL_DIGIT = 0
TOKEN_DIGIT = 1
TOKEN_LETTER = 2
TOKEN_SUFFIX = 3
TOKEN_SUFFIX_NO = 4
TOKEN_COMMIT_HASH = 5
TOKEN_REVISION_NO = 6
TOKEN_END = 7
TOKEN_INVALID = 8

SUFFIX_INVALID = 0
SUFFIX_ALPHA = 1
SUFFIX_BETA = 2
SUFFIX_PRE = 3
SUFFIX_RC = 4
SUFFIX_NONE = 5
SUFFIX_CVS = 6
SUFFIX_SVN = 7
SUFFIX_GIT = 8
SUFFIX_HG = 9
SUFFIX_P = 10

LESS = 1
EQUAL = 2
GREATER = 4
FUZZY = 8

OP_MASK = {
    '<': LESS,
    '<=': LESS | EQUAL,
    '>': GREATER,
    '>=': GREATER | EQUAL,
    '=': EQUAL,
    '~': FUZZY | EQUAL,
    '<~': LESS | EQUAL | FUZZY,
    '>~': GREATER | EQUAL | FUZZY,
}

_SUFFIX = {
    'alpha': SUFFIX_ALPHA,
    'beta': SUFFIX_BETA,
    'pre': SUFFIX_PRE,
    'rc': SUFFIX_RC,
    'cvs': SUFFIX_CVS,
    'svn': SUFFIX_SVN,
    'git': SUFFIX_GIT,
    'hg': SUFFIX_HG,
    'p': SUFFIX_P,
}

_NUMERIC = (
    TOKEN_INITIAL_DIGIT,
    TOKEN_DIGIT,
    TOKEN_SUFFIX_NO,
    TOKEN_REVISION_NO,
)

_HEX = set('0123456789abcdefABCDEF')


class Token:
    """Один фрагмент строки версии."""

    def __init__(self, kind, number, text, suffix, rest):
        """Сохранить фрагмент и непрочитанный хвост строки."""
        self.kind = kind
        self.number = number
        self.text = text
        self.suffix = suffix
        self.rest = rest


def is_valid_version(text):
    """Проверить, что строка является версией пакета Alpine."""
    if text == '':
        return False
    token = token_first(text)
    while token.kind < TOKEN_END:
        token = token_next(token)
    return token.kind == TOKEN_END


def version_matches(actual, operator, required):
    """Проверить ограничение версии из поля зависимости."""
    if operator == '':
        return True
    mask = OP_MASK[operator]
    fuzzy = (mask & FUZZY) != ZERO
    result = compare(actual, required, fuzzy)
    return (result & mask) != ZERO


def compare(left, right, fuzzy=False):
    """Сравнить две версии и вернуть LESS, EQUAL или GREATER."""
    left_token = token_first(left)
    right_token = token_first(right)
    while _same_open(left_token, right_token):
        result = token_cmp(left_token, right_token)
        if result != EQUAL:
            return result
        left_token = token_next(left_token)
        right_token = token_next(right_token)
    return _finish(left_token, right_token, fuzzy)


def token_cmp(left_token, right_token):
    """Сравнить два фрагмента одного типа."""
    if _digit_as_text(left_token, right_token):
        return _cmp_text(left_token.text, right_token.text)
    if left_token.kind in _NUMERIC:
        return _cmp_int(left_token.number, right_token.number)
    if left_token.kind == TOKEN_LETTER:
        return _cmp_text(left_token.text, right_token.text)
    if left_token.kind == TOKEN_SUFFIX:
        return _cmp_int(left_token.suffix, right_token.suffix)
    return _cmp_text(left_token.text, right_token.text)


def token_first(text):
    """Прочитать первое число версии."""
    return _take_digits(TOKEN_INITIAL_DIGIT, text)


def token_next(token):
    """Прочитать следующий фрагмент после token."""
    if token.rest == '':
        return _end()
    return _dispatch(token, token.rest)


def _same_open(left_token, right_token):
    """Оба фрагмента одного типа и строка версии еще не кончилась."""
    return (
        left_token.kind == right_token.kind
        and left_token.kind < TOKEN_END
    )


def _digit_as_text(left_token, right_token):
    """Число с ведущим нулем apk сравнивает как строку."""
    if left_token.kind != TOKEN_DIGIT:
        return False
    left_zero = left_token.text.startswith('0')
    right_zero = right_token.text.startswith('0')
    return left_zero or right_zero


def _cmp_int(left, right):
    """Сравнить два целых числа."""
    if left < right:
        return LESS
    if left > right:
        return GREATER
    return EQUAL


def _cmp_text(left, right):
    """Сравнить две строки по порядку символов."""
    if left < right:
        return LESS
    if left > right:
        return GREATER
    return EQUAL


def _finish(left_token, right_token, fuzzy):
    """Дорешать сравнение, когда фрагменты разошлись."""
    if left_token.kind == right_token.kind:
        return EQUAL
    if right_token.kind == TOKEN_END and fuzzy:
        return EQUAL
    if _prerelease(left_token):
        return LESS
    if _prerelease(right_token):
        return GREATER
    if left_token.kind > right_token.kind:
        return LESS
    if right_token.kind > left_token.kind:
        return GREATER
    return EQUAL


def _prerelease(token):
    """Суффикс alpha, beta, pre или rc меньше обычной версии."""
    return token.kind == TOKEN_SUFFIX and token.suffix < SUFFIX_NONE


def _dispatch(token, rest):
    """Выбрать разбор по первому символу хвоста."""
    first = rest[0]
    if first.islower():
        return _letter(token, rest)
    if first == '.':
        return _dotted(token, rest)
    if first.isdigit():
        return _number(token, rest)
    if first == '_':
        return _suffix(token, rest)
    if first == '~':
        return _hash(token, rest)
    if first == '-':
        return _revision(token, rest)
    return _invalid()


def _letter(token, rest):
    """Прочитать одну букву версии."""
    if token.kind > TOKEN_DIGIT:
        return _invalid()
    return Token(TOKEN_LETTER, ZERO, rest[0], SUFFIX_INVALID, rest[1:])


def _dotted(token, rest):
    """Прочитать число после точки."""
    if token.kind > TOKEN_DIGIT:
        return _invalid()
    return _take_digits(TOKEN_DIGIT, rest[1:])


def _number(token, rest):
    """Прочитать число без точки перед ним."""
    kind = _number_kind(token)
    if kind is None:
        return _invalid()
    return _take_digits(kind, rest)


def _number_kind(token):
    """Тип числового фрагмента по предыдущему фрагменту."""
    if token.kind in (TOKEN_INITIAL_DIGIT, TOKEN_DIGIT):
        return TOKEN_DIGIT
    if token.kind == TOKEN_SUFFIX:
        return TOKEN_SUFFIX_NO
    return None


def _suffix(token, rest):
    """Прочитать суффикс после знака подчеркивания."""
    if token.kind > TOKEN_SUFFIX_NO:
        return _invalid()
    text, tail = _pull_lower(rest[1:])
    code = _SUFFIX.get(text, SUFFIX_INVALID)
    if code == SUFFIX_INVALID:
        return _invalid()
    return Token(TOKEN_SUFFIX, ZERO, text, code, tail)


def _hash(token, rest):
    """Прочитать хэш коммита после знака тильды."""
    if token.kind >= TOKEN_COMMIT_HASH:
        return _invalid()
    text, tail = _pull_hex(rest[1:])
    if text == '':
        return _invalid()
    return Token(TOKEN_COMMIT_HASH, ZERO, text, SUFFIX_INVALID, tail)


def _revision(token, rest):
    """Прочитать номер ревизии пакета после -r."""
    if token.kind >= TOKEN_REVISION_NO:
        return _invalid()
    if not rest.startswith('-r'):
        return _invalid()
    return _take_digits(TOKEN_REVISION_NO, rest[len('-r'):])


def _take_digits(kind, rest):
    """Забрать десятичное число с начала строки."""
    raw, tail = _pull_digits(rest)
    if raw is None:
        return _invalid()
    return Token(kind, int(raw), raw, SUFFIX_INVALID, tail)


def _pull_digits(rest):
    """Отделить ведущие цифры."""
    index = ZERO
    while index < len(rest) and rest[index].isdigit():
        index += 1
    if index == ZERO:
        return None, rest
    return rest[:index], rest[index:]


def _pull_lower(rest):
    """Отделить ведущие строчные буквы."""
    index = ZERO
    while index < len(rest) and rest[index].islower():
        index += 1
    return rest[:index], rest[index:]


def _pull_hex(rest):
    """Отделить ведущие шестнадцатеричные цифры."""
    index = ZERO
    while index < len(rest) and rest[index] in _HEX:
        index += 1
    return rest[:index], rest[index:]


def _end():
    """Фрагмент конца строки."""
    return Token(TOKEN_END, ZERO, '', SUFFIX_INVALID, '')


def _invalid():
    """Фрагмент, который apk считает ошибкой разбора."""
    return Token(TOKEN_INVALID, ZERO, '', SUFFIX_INVALID, '')
