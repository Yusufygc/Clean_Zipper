"""V2 denetim şablonu biçiminde Markdown raporu (A özet, B iyi pratikler, C incelenmeyenler, D bulgular, E plan, F soru)."""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from src.core.interfaces import IReporter
from src.models.analysis_models import AnalysisResult, ProjectAnalysis, Severity
from src.services import audit_catalog as catalog
from src.services import audit_evidence as source_evidence

logger = logging.getLogger(__name__)

TABLE_LIMIT = 15                  # A bölümü tablosundaki en fazla grup
DETAIL_LIMIT = 25                 # D bölümündeki en fazla bulgu
DETAIL_PER_RULE = 3               # aynı kuraldan D bölümüne en fazla bulgu (910 benzer bulgu raporu boğmasın)
PLAN_SLICES = ((Severity.CRITICAL, '24 saat içinde'), (Severity.HIGH, 'Bu hafta'), (Severity.MEDIUM, 'Bu ay'))


@dataclass
class _Group:
    """Aynı kurala (kural yoksa kategori + başlığa) ve aynı önceliğe ait bulgular."""
    rule: str
    label: str
    category: str
    severity: Severity
    findings: List[AnalysisResult] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def effort(self) -> str:
        return catalog.effort_of(self.rule, self.severity, self.count)


def _cell(value) -> str:
    """Tablo hücresi: satır sonu ve `|` hücreyi bozmasın."""
    return str(value).replace('\r', ' ').replace('\n', ' ').replace('|', '\\|').strip()


def _inline(value) -> str:
    return str(value).replace('\r', ' ').replace('\n', ' ').replace('`', "'").strip()


def _fence(text: str) -> str:
    """İçindeki en uzun ``` dizisinden uzun çit; kanıt kod bloğundan taşamasın."""
    longest = run = 0
    for char in text:
        run = run + 1 if char == '`' else 0
        longest = max(longest, run)
    return '`' * max(3, longest + 1)


def _category_label(category: str) -> str:
    return catalog.CATEGORY_NAMES.get(category, category)


def _find_rule(analysis: ProjectAnalysis, rule: str) -> List[AnalysisResult]:
    return [f for f in analysis.all_findings if f.metadata.get('rule') == rule]


def _build_groups(analysis: ProjectAnalysis) -> List[_Group]:
    by_key: Dict[Tuple[str, Severity], _Group] = {}
    for finding in analysis.all_findings:
        if finding.severity not in catalog.SEVERITY_LABELS:
            continue                                              # BİLGİ bulguları tablo satırı olmaz
        rule = finding.metadata.get('rule') or ''
        generic = finding.title.partition(': ')[0]
        key = (rule or f"{finding.category}:{generic}", finding.severity)
        group = by_key.get(key)
        if group is None:
            group = by_key[key] = _Group(rule, catalog.RULE_LABELS.get(rule, generic), finding.category, finding.severity)
        group.findings.append(finding)
    for group in by_key.values():
        group.findings.sort(key=lambda f: str(f.file_path or ''))
    return sorted(by_key.values(), key=lambda g: (-g.severity.value, -g.count, g.label))


class AuditReportService(IReporter):
    """Analiz sonucunu V2 denetim şablonuna uygun, sabit yapılı bir Markdown raporuna dönüştürür."""

    def generate_report(self, analysis: ProjectAnalysis) -> str:
        groups = _build_groups(analysis)
        parts = [self._summary(analysis, groups), self._good_practices(analysis), self._not_reviewed(analysis),
                 self._details(analysis, groups), self._action_plan(groups), self._next_step(groups)]
        return '\n\n'.join(parts) + '\n'

    def export_report(self, analysis: ProjectAnalysis, output_path: Path) -> bool:
        try:
            Path(output_path).write_text(self.generate_report(analysis), encoding='utf-8')
            return True
        except Exception:
            logger.exception("Denetim raporu dışa aktarılamadı: %s", output_path)
            return False

    # ---- A: yönetici özeti ---------------------------------------------------------------------------------

    def _summary(self, analysis: ProjectAnalysis, groups: List[_Group]) -> str:
        counts = {severity: 0 for severity in catalog.SEVERITY_LABELS}
        for group in groups:
            counts[group.severity] += group.count
        lines = [
            f"# Denetim Raporu: {_inline(analysis.project_path.name)}", "",
            f"- **Tarih:** {analysis.analysis_time.strftime('%d.%m.%Y %H:%M')}",
            f"- **Konum:** `{_inline(analysis.project_path)}`",
            f"- **Kapsam:** {analysis.total_files} dosya, {analysis.total_dirs} klasör, {analysis.total_size_mb:.1f} MB",
            f"- **Genel not:** {analysis.health_score:.0f}/100 ({analysis.health_status.value})", "",
            "## A. Yönetici özeti", "",
            "Bulgu sayıları: " + ', '.join(f"{catalog.badge(s)} {counts[s]}" for s in catalog.SEVERITY_LABELS) + ".", "",
        ]
        lines += self._category_table(analysis) + ['']
        lines += self._findings_table(groups)
        return '\n'.join(lines)

    @staticmethod
    def _category_table(analysis: ProjectAnalysis) -> List[str]:
        if not analysis.category_scores:
            return []
        rows = ["| Kategori | Puan |", "|---|---|"]
        for category, score in sorted(analysis.category_scores.items(), key=lambda item: item[1]):
            rows.append(f"| {_cell(_category_label(category))} | {score:.0f} |")
        return rows

    @staticmethod
    def _findings_table(groups: List[_Group]) -> List[str]:
        if not groups:
            return ["Öncelikli bulgu yok."]
        rows = ["| # | Bulgu | Öncelik | Boyut | Efor | Etki |", "|---|---|---|---|---|---|"]
        for number, group in enumerate(groups[:TABLE_LIMIT], 1):
            impact = catalog.impact_of(group.rule, group.category)
            rows.append(f"| {number} | {_cell(group.label)} ({group.count}) | {catalog.badge(group.severity)} | "
                        f"{catalog.dimension(group.category)} | {group.effort} | {_cell(impact)} |")
        if len(groups) > TABLE_LIMIT:
            rows += ["", f"_{len(groups) - TABLE_LIMIT} bulgu grubu daha var; ayrıntı için analiz çıktısına bakın._"]
        return rows

    # ---- B: iyi pratikler ----------------------------------------------------------------------------------

    def _good_practices(self, analysis: ProjectAnalysis) -> str:
        practices = self._hygiene_practices(analysis) + self._absence_practices(analysis) + self._test_practice(analysis)
        body = '\n'.join(f"- ✅ {p}" for p in practices) or "- Belirgin bir olumlu tespit yok."
        return f"## B. İyi pratikler\n\n{body}"

    @staticmethod
    def _hygiene_practices(analysis: ProjectAnalysis) -> List[str]:
        summary = _find_rule(analysis, 'hygiene-summary')
        present = summary[0].metadata.get('present', []) if summary else []
        return [catalog.HYGIENE_GOOD[key] for key in present if key in catalog.HYGIENE_GOOD]

    @staticmethod
    def _absence_practices(analysis: ProjectAnalysis) -> List[str]:
        """İlgili analizör çalışmış ve kötü bulgu çıkmamışsa olumlu tespit."""
        def none_of(*rules):
            return lambda: not any(_find_rule(analysis, rule) for rule in rules)

        def no_serious_security():
            return not any(f.category == 'security' and f.severity.value >= Severity.HIGH.value for f in analysis.all_findings)

        checks = (
            ('security', no_serious_security, "Yüksek öncelikli güvenlik bulgusu yok"),
            ('architecture', none_of('import-cycle'), "Döngüsel bağımlılık yok"),
            ('duplicate', none_of('code-clone'), "Anlamlı kod klonu yok"),
            ('dependency', none_of('unpinned-dependencies'), "Bağımlılıklar sürüme sabitlenmiş"),
            ('reliability', none_of('bare-except', 'swallowed-exception'), "Hatalar yutulmuyor (çıplak ya da sessiz except yok)"),
        )
        return [text for category, holds, text in checks if category in analysis.category_scores and holds()]

    @staticmethod
    def _test_practice(analysis: ProjectAnalysis) -> List[str]:
        summary = _find_rule(analysis, 'test-summary')
        if not summary:
            return []
        meta = summary[0].metadata
        return [f"{meta.get('test_functions', 0)} test işlevi, {meta.get('test_files', 0)} test dosyası "
                f"(test/kaynak satır oranı {meta.get('ratio', 0):.2f})"]

    # ---- C: incelenmeyenler ---------------------------------------------------------------------------------

    def _not_reviewed(self, analysis: ProjectAnalysis) -> str:
        items = self._skipped_items(analysis)
        approximate = sorted(lang for lang in analysis.language_stats if lang != 'python')
        if approximate:
            items.append("Python dışındaki diller (" + ', '.join(approximate) + ") sözcük tabanlı çözümlendi; sonuçlar yaklaşıktır")
        if not any(f.category == 'git' for f in analysis.all_findings):
            items.append("Git geçmişi (sıcak nokta, birlikte değişim, geçmişteki sırlar) için bulgu yok: "
                         "depo değil, git kurulu değil ya da geçmiş kısa olabilir")
        items.append("Bu aracın kapsamı dışında: bilinen zafiyet (CVE) taraması, lisans uyumu, çalışma zamanı performansı, "
                     "yürütülen kodun davranışı")
        return "## C. İncelenmedi\n\n" + '\n'.join(f"- {item}" for item in items)

    @staticmethod
    def _skipped_items(analysis: ProjectAnalysis) -> List[str]:
        """Analize girmeyen dosyalar, hata veren analizörler ve .gitignore ile dışarıda kalanlar."""
        items = [f"{catalog.SKIP_REASONS.get(reason, reason)}: {count}" for reason, count in analysis.skipped_files.items()]
        if analysis.failed_analyzers:
            items.append("Hata veren analizörler (sonuçları eksik): " + ', '.join(analysis.failed_analyzers))
        ignored = analysis.ignored_by_gitignore
        if analysis.gitignore_applied and any(ignored.values()):
            items.append(f".gitignore kuralıyla dışarıda bırakıldı: {ignored.get('files', 0)} dosya, {ignored.get('dirs', 0)} klasör")
        return items

    # ---- D: ayrıntılı bulgular ------------------------------------------------------------------------------

    def _details(self, analysis: ProjectAnalysis, groups: List[_Group]) -> str:
        blocks: List[str] = []
        for group in groups:
            for finding in group.findings[:DETAIL_PER_RULE]:
                if len(blocks) < DETAIL_LIMIT:
                    blocks.append(self._detail_block(analysis, group, finding, len(blocks) + 1))
        if not blocks:
            return "## D. Ayrıntılı bulgular\n\nAyrıntılı bulgu yok."
        note = f"_Her kuraldan en fazla {DETAIL_PER_RULE} örnek, toplam en fazla {DETAIL_LIMIT} bulgu gösterilir._"
        return "## D. Ayrıntılı bulgular\n\n" + '\n\n'.join(blocks) + "\n\n" + note

    @staticmethod
    def _detail_block(analysis: ProjectAnalysis, group: _Group, finding: AnalysisResult, number: int) -> str:
        location = source_evidence.relative(analysis.project_path, finding.file_path)
        line = source_evidence.line_of(finding)
        if line:
            location += f":{line}"
        category = _category_label(finding.category)
        dimension = catalog.dimension(finding.category)
        lines = [
            f"### D{number}. {catalog.badge(finding.severity)}: {_inline(finding.title)}", "",
            f"- **Dosya / Konum:** `{_inline(location)}`",
            f"- **Kategori:** {dimension if dimension == category else f'{dimension} ({category})'}",
            f"- **Sorun:** {_inline(finding.description)}",
            f"- **Etki:** {catalog.impact_of(group.rule, group.category)}",
        ]
        snippet = source_evidence.evidence(finding, line)
        if snippet:
            fence = _fence(snippet)
            lines += ["- **Kanıt:**", "", fence, snippet, fence, ""]
        else:
            lines.append("- **Kanıt:** (kod parçası gösterilmiyor)")
        lines += [f"- **Çözüm:** {_inline(finding.recommendation or 'Bulguyu inceleyip gerekçeli biçimde düzeltin.')}",
                  f"- **Efor:** {catalog.EFFORT_TEXT[catalog.effort_of(group.rule, finding.severity)]}",
                  f"- **Bağımlılık:** {catalog.RULE_DEPENDENCY.get(group.rule, 'Yok')}"]
        return '\n'.join(lines)

    # ---- E: aksiyon planı -------------------------------------------------------------------------------------

    def _action_plan(self, groups: List[_Group]) -> str:
        sections = ["## E. Aksiyon planı"]
        for severity, title in PLAN_SLICES:
            sections.append(self._plan_slice(title, severity, [g for g in groups if g.severity == severity]))
        low = [g for g in groups if g.severity == Severity.LOW]
        if low:
            labels = ', '.join(_inline(g.label) for g in low[:3])
            sections.append(f"### Fırsat oldukça\n\n{catalog.badge(Severity.LOW)}: {len(low)} grup, "
                            f"{sum(g.count for g in low)} bulgu (öne çıkanlar: {labels}). Dokunulan dosyalarda birlikte düzeltin.")
        return '\n\n'.join(sections)

    @staticmethod
    def _plan_slice(title: str, severity: Severity, chosen: List[_Group]) -> str:
        heading = f"### {title} ({catalog.badge(severity)})"
        if not chosen:
            return f"{heading}\n\nBu dilimde iş yok."
        rows = ["| Eylem | Beklenen sonuç | Bağımlılık | Risk |", "|---|---|---|---|"]
        for group in chosen:
            action = f"{group.label} ({group.count} bulgu, efor {group.effort}): önerilen çözümü uygula"
            result = f"{group.count} bulgu kapanır; {_category_label(group.category)} puanı yükselir"
            rows.append(f"| {_cell(action)} | {_cell(result)} | {_cell(catalog.RULE_DEPENDENCY.get(group.rule, 'Yok'))} | "
                        f"{_cell(catalog.RULE_RISK.get(group.rule, catalog.DEFAULT_RISK))} |")
        return heading + "\n\n" + '\n'.join(rows)

    # ---- F: sonraki adım ---------------------------------------------------------------------------------------

    @staticmethod
    def _next_step(groups: List[_Group]) -> str:
        if not groups:
            return "## F. Sonraki adım\n\nÖncelikli bulgu çıkmadı. Eşikleri sıkılaştırıp analizi yeniden çalıştırmamı ister misiniz?"
        first = groups[0]
        return (f"## F. Sonraki adım\n\nEn yüksek öncelikli grup **{_inline(first.label)}** ({first.count} bulgu). "
                "Bu gruptan başlayıp düzeltmeleri uygulamamı mı, yoksa önce başka bir grubu mu ele almamı istersiniz?")
