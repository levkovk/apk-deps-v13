"""Диаграмма PlantUML."""

import unittest

from src.plantuml import to_plantuml


class PlantTest(unittest.TestCase):
    """Текст диаграммы для цепочки, пустого пакета и цикла."""

    def test_chain(self):
        """У ребра есть стрелка PlantUML."""
        graph = {'A': ['B'], 'B': ['C'], 'C': []}
        text = to_plantuml(graph, 'A')
        self.assertTrue(text.startswith('@startuml'))
        self.assertIn('"A" --> "B"', text)
        self.assertIn('"B" --> "C"', text)
        self.assertTrue(text.endswith('@enduml'))

    def test_single(self):
        """Пакет без зависимостей остается узлом."""
        text = to_plantuml({'musl': []}, 'musl')
        self.assertEqual(text, '@startuml\n"musl"\n@enduml')

    def test_cycle_edge(self):
        """Обратное ребро цикла тоже попадает в диаграмму."""
        graph = {'A': ['B'], 'B': ['A']}
        text = to_plantuml(graph, 'A')
        self.assertIn('"B" --> "A"', text)


if __name__ == '__main__':
    unittest.main()
