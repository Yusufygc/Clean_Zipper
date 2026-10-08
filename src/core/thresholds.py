"""Kod kalitesi eşikleri. Varsayılanlar V2 denetim şablonunun "Ölçüm Eşikleri" tablosudur.

Bir değer eşiği AŞARSA (> eşik) bulgu üretilir; eşiğin `severe_factor` katı ve üstü bir seviye yukarı raporlanır.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class QualityThresholds:
    cyclomatic: int = 10          # siklomatik karmaşıklık
    cognitive: int = 15           # bilişsel karmaşıklık (Sonar)
    function_lines: int = 50
    class_lines: int = 300
    file_lines: int = 500
    parameters: int = 5
    nesting: int = 4              # iç içe kontrol bloğu derinliği
    class_methods: int = 20
    module_imports: int = 25      # dosya başına benzersiz import
    severe_factor: float = 2.0

    def is_severe(self, value: float, threshold: float) -> bool:
        return value >= threshold * self.severe_factor
