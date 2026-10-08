"""Dil bağımsız kaynak kod ölçüm modelleri."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    start_line: int   # 1 tabanlı, dahil
    end_line: int
    complexity: int   # siklomatik karmaşıklık, taban 1

    @property
    def lines(self) -> int:
        return self.end_line - self.start_line + 1


@dataclass(frozen=True)
class ClassInfo:
    name: str
    start_line: int
    end_line: int
    method_count: int

    @property
    def lines(self) -> int:
        return self.end_line - self.start_line + 1


@dataclass
class SourceMetrics:
    language: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)   # ham belirteçler (ör. 'os.path', 'react', 'java.util.List')
    approximate: bool = False                          # sözcük tabanlı çözümlemede True
    parse_ok: bool = True                              # yapı çıkarılabildi mi (Python'da sözdizimi hatası -> False)


class LanguageSupport(ABC):
    id: str
    display_name: str
    extensions: Tuple[str, ...]
    approximate: bool = False

    @abstractmethod
    def analyze(self, text: str) -> SourceMetrics:
        """Kaynak metinden ölçümleri çıkarır. Çağıran, dosya başına hataları yalıtır."""

    def refine(self, text: str) -> str:
        """Dosya içeriğine bakarak asıl dil kimliğini döner (ör. .h -> c / cpp)."""
        return self.id
