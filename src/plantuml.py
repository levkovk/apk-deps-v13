"""Текст диаграммы PlantUML."""


def to_plantuml(graph, root):
    """Описание графа на языке PlantUML."""
    lines = ['@startuml']
    edges = edge_lines(graph)
    if edges:
        lines.extend(edges)
    else:
        lines.append(f'"{root}"')
    lines.append('@enduml')
    return '\n'.join(lines)


def edge_lines(graph):
    """Строки ребер диаграммы."""
    lines = []
    for name, deps in graph.items():
        for dep in deps:
            lines.append(f'"{name}" --> "{dep}"')
    return lines
