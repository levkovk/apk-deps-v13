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
