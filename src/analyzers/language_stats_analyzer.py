from typing import Dict, List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.languages import default_languages, parse_file
from src.models.analysis_models import AnalysisResult, Severity

COUNTERS = ('files', 'total_lines', 'code_lines', 'comment_lines', 'blank_lines')


@register_analyzer
class LanguageStatsAnalyzer(BaseAnalyzer):
    """Dil başına dosya ve satır dağılımı (bilgi amaçlı, puanlanmaz)."""

    def __init__(self, priority: int = 22):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Dil İstatistikleri Analizörü"

    @property
    def category(self) -> str:
        return "type"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        totals: Dict[str, Dict[str, int]] = {}
        approximate: Dict[str, bool] = {}
        for entry in index.files:
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            bucket = totals.setdefault(metrics.language, dict.fromkeys(COUNTERS, 0))
            bucket['files'] += 1
            for counter in COUNTERS[1:]:
                bucket[counter] += getattr(metrics, counter)
            approximate[metrics.language] = metrics.approximate

        results = []
        for language_id, bucket in sorted(totals.items(), key=lambda kv: kv[1]['code_lines'], reverse=True):
            display = default_languages.get(language_id).display_name
            results.append(self._create_result(
                title=f"Dil: {display}",
                description=(f"{bucket['files']} dosya, {bucket['code_lines']} kod, "
                             f"{bucket['comment_lines']} yorum, {bucket['blank_lines']} boş satır"),
                severity=Severity.INFO,
                kind='language_stats', language=language_id, approximate=approximate[language_id], **bucket,
            ))
        return results
