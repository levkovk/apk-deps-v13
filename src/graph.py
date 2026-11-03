"""Обход графа зависимостей в ширину, без рекурсии."""

from collections import deque

ZERO = 0


def skipped(name, skip):
    """Пакет не учитывается, если в имени есть подстрока фильтра."""
    return skip != '' and skip in name


def bfs_graph(root, forward, skip):
    """Граф зависимостей обходом BFS. Повторный заход не делается."""
    if skipped(root, skip):
        return {}
    graph = {}
    seen = {root}
    queue = deque([root])
    while queue:
        node = queue.popleft()
        graph[node] = _children(node, forward, skip, seen, queue)
    return graph


def _children(node, forward, skip, seen, queue):
    """Прямые зависимости узла. Новые узлы ставятся в очередь."""
    children = []
    for dep in forward.get(node, []):
        if skipped(dep, skip):
            continue
        children.append(dep)
        if dep not in seen:
            seen.add(dep)
            queue.append(dep)
    return children


def format_graph(graph):
    """Текстовый граф: ребра и, если есть, пакеты из цикла."""
    if not graph:
        return 'пакет исключен фильтром'
    parts = []
    edges = format_edges(graph)
    if edges != '':
        parts.append(edges)
    cycles = format_cycles(graph)
    if cycles != '':
        parts.append(cycles)
    if not parts:
        return 'зависимостей нет'
    return '\n'.join(parts)


def format_edges(graph):
    """Строки вида «A -> B»."""
    lines = []
    for name, deps in graph.items():
        for dep in deps:
            lines.append(f'{name} -> {dep}')
    return '\n'.join(lines)


def format_cycles(graph):
    """Строка «цикл: ...» или пустая строка, если цикла нет."""
    nodes = cycle_nodes(graph)
    if not nodes:
        return ''
    return 'цикл: ' + ' '.join(nodes)


def cycle_nodes(graph):
    """Имена пакетов, которые входят в цикл."""
    indegree = _indegree(graph)
    left = dict(indegree)
    queue = deque(_zeros(indegree))
    while queue:
        _relax(graph, queue.popleft(), left, queue)
    return [name for name, degree in left.items() if degree > ZERO]


def _zeros(indegree):
    """Узлы, в которые не входит ни одного ребра."""
    return [name for name, degree in indegree.items() if degree == ZERO]


def _indegree(graph):
    """Сколько ребер входит в каждый узел."""
    indegree = {name: ZERO for name in graph}
    for deps in graph.values():
        for dep in deps:
            indegree[dep] = indegree.get(dep, ZERO) + 1
    return indegree


def _relax(graph, name, left, queue):
    """Убрать ребра из узла, как в алгоритме Кана."""
    for dep in graph.get(name, []):
        left[dep] -= 1
        if left[dep] == ZERO:
            queue.append(dep)


def format_reverse(root, forward, skip):
    """Обратные зависимости: кто зависит от пакета, по одному в строке."""
    if skipped(root, skip):
        return 'пакет исключен фильтром'
    names = reverse_from(root, forward, skip)
    if not names:
        return 'обратных зависимостей нет'
    return '\n'.join(names)


def reverse_from(root, forward, skip):
    """Пакеты, которые прямо или косвенно зависят от root."""
    if skipped(root, skip):
        return []
    return _walk(root, _invert(forward, skip))


def _invert(forward, skip):
    """Развернуть ребра: зависимость -> пакеты, которым она нужна."""
    rev = {}
    for name, deps in forward.items():
        if skipped(name, skip):
            continue
        _link(rev, name, deps, skip)
    return rev


def _link(rev, name, deps, skip):
    """Добавить обратные ребра одного пакета."""
    for dep in deps:
        if skipped(dep, skip):
            continue
        rev.setdefault(dep, []).append(name)


def _walk(root, graph):
    """BFS от root по уже развернутым ребрам. Сам root не входит."""
    seen = {root}
    queue = deque([root])
    found = []
    while queue:
        _take(queue, graph, seen, found)
    return found


def _take(queue, graph, seen, found):
    """Забрать узел из очереди и поставить новых соседей."""
    node = queue.popleft()
    for dep in graph.get(node, []):
        if dep in seen:
            continue
        seen.add(dep)
        found.append(dep)
        queue.append(dep)
