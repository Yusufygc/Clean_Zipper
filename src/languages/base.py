"""Dil bağımsız kaynak kod ölçüm modelleri."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    start_line: int   # 1 tabanlı, dahil
    end_line: int
    complexity: int   # siklomatik karmaşıklık, taban 1
    params: int = 0       # parametre sayısı (self/cls/this hariç)
    max_nesting: int = 0  # en derin iç içe kontrol bloğu (if/for/while/try/switch/catch ...)
    cognitive: int = 0    # bilişsel karmaşıklık (Sonar kuralları; Python kesin, diğer diller yaklaşık)

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


@dataclass(frozen=True)
class ImportRef:
    """Python içe aktarması: `import a.b` -> ('a.b', 0, ()); `from ..x import y, z` -> ('x', 2, ('y', 'z'))."""
    module: str
    level: int            # 0 mutlak, 1 = `.`, 2 = `..` ...
    names: Tuple[str, ...]
    line: int


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
    # Yalnızca Python: modül yüklenirken çalışan (fonksiyon dışı, TYPE_CHECKING dışı) içe aktarmalar; döngü tespiti için
    import_refs: List[ImportRef] = field(default_factory=list)
    approximate: bool = False                          # sözcük tabanlı çözümlemede True
    parse_ok: bool = True                              # yapı çıkarılabildi mi (Python'da sözdizimi hatası -> False)


@dataclass(frozen=True)
class StrippedSource:
    """Aynı uzunlukta, yorum/string içeriği boşlukla değiştirilmiş kaynak (satır numaraları korunur)."""
    no_comments: str    # yorumlar silinmiş, string içeriği duruyor (içe aktarma yolu, algoritma adı gibi veriler için)
    clean: str          # yorum VE string silinmiş (yapı / kalıp analizi için)


class LanguageSupport(ABC):
    id: str
    display_name: str
    extensions: Tuple[str, ...]
    approximate: bool = False

    @abstractmethod
    def analyze(self, text: str) -> SourceMetrics:
        """Kaynak metinden ölçümleri çıkarır. Çağıran, dosya başına hataları yalıtır."""

    def stripped(self, text: str) -> Optional[StrippedSource]:
        """Yorum/string temizlenmiş görünüm; desteklemeyen dilde None."""
        return None

    def refine(self, text: str) -> str:
        """Dosya içeriğine bakarak asıl dil kimliğini döner (ör. .h -> c / cpp)."""
        return self.id
