import re
from typing import Dict, List

from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.languages.import_graph import (Graph, js_graph, python_graph, shortest_cycle,
                                        strongly_connected_components)
from src.languages.registry import get_stripped
from src.models.analysis_models import AnalysisResult, Severity

JS_LANGUAGES = frozenset({'javascript', 'typescript'})
LARGE_CYCLE = 4                  # bu kadar dosyalık döngü YÜKSEK
MAX_LISTED = 8
TOP_N = 5
_TYPE_ONLY = re.compile(
    r'''(?m)^[ \t]*(?:import|export)\s+type\b[^'"\n;]*?\bfrom\s+['"]([^'"\n]+)['"]''')


@register_analyzer
class ArchitectureAnalyzer(BaseAnalyzer):
    """Dosya bağımlılık grafiği: döngüsel bağımlılıklar (Tarjan SCC) ve bağımlılık özeti.

    Python: modül yüklenirken çalışan importlar (fonksiyon içi ve `TYPE_CHECKING` importları döngü sayılmaz).
    JS/TS: göreli ve `@/` `~/` belirteçleri; `import type` kenar sayılmaz. Çözülemeyen (harici) importlar grafiğe girmez.
    Python dışı sonuçlar yaklaşık işaretlidir.
    """

    def __init__(self, priority: int = 30):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Mimari Bağımlılık Analizörü"

    @property
    def category(self) -> str:
        return "architecture"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        python_refs: Dict[str, list] = {}
        js_imports: Dict[str, list] = {}
        for entry in index.files:
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            if metrics.language == 'python' and metrics.parse_ok:
                python_refs[entry.rel] = metrics.import_refs
            elif metrics.language in JS_LANGUAGES:
                js_imports[entry.rel] = self._value_imports(index, entry, metrics.imports)
        results: List[AnalysisResult] = []
        for language, graph, approximate in (('python', python_graph(python_refs), False),
                                             ('javascript', js_graph(js_imports), True)):
            results.extend(self._report(index, language, graph, approximate))
        return results

    @staticmethod
    def _value_imports(index: ProjectIndex, entry, imports: List[str]) -> List[str]:
        """`import type ... from` belirteçleri çıkarılır (çalışma zamanında yoktur)."""
        stripped = get_stripped(index, entry)
        if stripped is None:
            return imports
        type_only = set(_TYPE_ONLY.findall(stripped.no_comments))
        return [spec for spec in imports if spec not in type_only]

    # ---- bulgu üretimi -------------------------------------------------------------------------------

    def _report(self, index: ProjectIndex, language: str, graph: Graph, approximate: bool) -> List[AnalysisResult]:
        edges = sum(len(targets) for targets in graph.values())
        if not edges:
            return []
        components = strongly_connected_components(graph)
        results = [self._cycle_result(index, graph, component, language, approximate) for component in components]
        results.append(self._summary(language, graph, edges, components, approximate))
        return results

    def _cycle_result(self, index: ProjectIndex, graph: Graph, component: List[str], language: str,
                      approximate: bool) -> AnalysisResult:
        cycle = shortest_cycle(graph, component)
        severity = Severity.HIGH if len(component) >= LARGE_CYCLE else Severity.MEDIUM
        path = " -> ".join(cycle[:MAX_LISTED + 1]) + (" -> ..." if len(cycle) > MAX_LISTED + 1 else "")
        extra = f" Bileşen toplam {len(component)} dosyadan oluşuyor." if len(component) > len(cycle) - 1 else ""
        return self._create_result(
            title=f"Döngüsel Bağımlılık: {len(component)} dosya ({component[0].rsplit('/', 1)[-1]} ...)",
            description=f"Dosyalar birbirini doğrudan veya dolaylı içe aktarıyor. En kısa döngü: {path}.{extra}",
            severity=severity, file_path=index.root / component[0],
            recommendation=("Ortak parçayı üçüncü bir modüle çıkarın veya bağımlılığı tersine çevirin "
                            "(arayüz / geri çağırma); geçici çözüm olarak içe aktarmayı fonksiyon içine taşıyın."),
            rule='import-cycle', files=component, cycle=cycle, size=len(component),
            language=language, approximate=approximate)

    def _summary(self, language: str, graph: Graph, edges: int, components: List[List[str]],
                 approximate: bool) -> AnalysisResult:
        fan_in: Dict[str, int] = {rel: 0 for rel in graph}
        for targets in graph.values():
            for target in targets:
                fan_in[target] += 1
        top_in = sorted(fan_in.items(), key=lambda item: (-item[1], item[0]))[:TOP_N]
        top_out = sorted(((rel, len(t)) for rel, t in graph.items()), key=lambda item: (-item[1], item[0]))[:TOP_N]
        files_in_cycles = sum(len(c) for c in components)
        return self._create_result(
            title=f"Bağımlılık Grafiği ({language}): {len(graph)} dosya, {edges} bağımlılık",
            description=(f"{len(graph)} dosya, {edges} proje içi bağımlılık, {len(components)} döngü "
                         f"({files_in_cycles} dosya döngüde). En çok kullanılan: "
                         f"{', '.join(f'{rel} ({n})' for rel, n in top_in if n)}."),
            severity=Severity.INFO,
            rule='dependency-graph', nodes=len(graph), edges=edges, cycles=len(components),
            files_in_cycles=files_in_cycles, top_fan_in=top_in, top_fan_out=top_out,
            language=language, approximate=approximate)
