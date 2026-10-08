"""Analiz bulgularını yapay zeka ajanının çalışabileceği görevlere çevirir: öğe çıkarma, kararlı parmak izi, dalgalara
ve partilere bölme, kapanış doğrulaması.

Parmak izi satır numarasına bağlı değildir (`kural + yol + ayırt edici ad + sıra`), bu yüzden bir düzeltme satırları
kaydırsa da aynı bulgu aynı kimliği taşır.
"""
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from src.models.analysis_models import AnalysisResult, ProjectAnalysis, Severity
from src.services import agent_guidance as guide
from src.services import audit_evidence as source_evidence

SCHEMA_VERSION = 1
DEFAULT_BATCH_SIZE = 15
MESSAGE_LIMIT = 400
MAX_NEW_REPORTED = 50
KIND_RULES = {'large_file': 'large-file', 'duplicate_group': 'duplicate-files', 'empty_dir': 'empty-folder',
              'sensitive_file': 'sensitive-file', 'total_size': 'project-size'}
# kuralın ayırt edici adını taşıyan metadata alanı (parmak izi için)
DISCRIMINATOR_KEYS = {'function-metrics': 'function', 'class-size': 'class_name', 'unused-dependency': 'dependency',
                      'tracked-artifacts': 'root'}


@dataclass
class TaskItem:
    fingerprint: str
    rule: str
    severity: str
    category: str
    path: str                                  # proje köküne göre, '/' ayraçlı
    line: Optional[int]
    lines: List[int]
    title: str
    message: str
    recommendation: str
    approximate: bool
    count: int
    wave: int
    evidence: Optional[str] = None             # JSON'a yazılmaz; yalnızca görev dosyasında gösterilir
    key: str = ''                              # parmak izi girdisi (ordinalsiz)

    def to_json(self) -> dict:
        return {'fingerprint': self.fingerprint, 'rule': self.rule, 'severity': self.severity, 'category': self.category,
                'path': self.path, 'line': self.line, 'lines': self.lines[:10], 'title': self.title, 'message': self.message,
                'recommendation': self.recommendation, 'approximate': self.approximate, 'count': self.count}


@dataclass
class Task:
    id: str
    wave: int
    rule: str
    label: str
    items: List[TaskItem] = field(default_factory=list)

    @property
    def guidance(self) -> guide.Guidance:
        return guide.guidance_for(self.rule, self.items[0].recommendation if self.items else None)

    @property
    def human(self) -> bool:
        return self.wave == guide.HUMAN_WAVE


def rule_of(finding: AnalysisResult) -> str:
    meta = finding.metadata
    return meta.get('rule') or KIND_RULES.get(meta.get('kind', ''), '') or finding.category


def _fingerprint(key: str, ordinal: int) -> str:
    return hashlib.sha1(f"{key}|{ordinal}".encode('utf-8')).hexdigest()[:12]


def _short(text: str) -> str:
    text = ' '.join(str(text).split())
    return text if len(text) <= MESSAGE_LIMIT else text[:MESSAGE_LIMIT - 1] + '…'


def _discriminator(finding: AnalysisResult, rule: str, project: Path) -> str:
    meta = finding.metadata
    if rule == 'code-clone':
        return '|'.join(sorted(loc['path'] for loc in meta.get('locations', [])))
    if rule == 'import-cycle':
        return '|'.join(sorted(meta.get('files', [])))
    if rule == 'duplicate-files':
        return '|'.join(sorted(source_evidence.relative(project, Path(p)) for p in meta.get('paths', [])))
    return str(meta.get(DISCRIMINATOR_KEYS.get(rule, ''), ''))


def _base_item(finding: AnalysisResult, rule: str, project: Path, detail: Tuple[str, Optional[int], str]) -> TaskItem:
    """`detail`: (ayırt edici ad, satır, ileti)."""
    discriminator, line, message = detail
    path = source_evidence.relative(project, finding.file_path)
    wave = guide.wave_of(rule, finding.category)
    snippet = None if wave == guide.HUMAN_WAVE else source_evidence.evidence(finding, line)
    raw_lines = finding.metadata.get('lines')                               # klon bulgusunda `lines` bir sayıdır
    lines = [n for n in raw_lines if isinstance(n, int)] if isinstance(raw_lines, list) else []
    raw_count = finding.metadata.get('count')
    return TaskItem(
        fingerprint='', rule=rule, severity=finding.severity.name, category=finding.category, path=path, line=line,
        lines=lines or ([line] if line else []), title=_short(finding.title), message=_short(message),
        recommendation=_short(finding.recommendation or ''), approximate=bool(finding.metadata.get('approximate')),
        count=raw_count if isinstance(raw_count, int) and raw_count > 0 else max(len(lines), 1), wave=wave, evidence=snippet,
        key=f"{rule}|{path}|{discriminator}")


def _expand(finding: AnalysisResult, rule: str, project: Path) -> List[TaskItem]:
    """Bir bulguyu görev öğelerine çevirir; birden çok kalemi olan bulgular (import, değişken) kalem başına öğe verir."""
    meta = finding.metadata
    if rule == 'unused-import':
        return [_base_item(finding, rule, project, (str(entry['name']), entry.get('line'),
                           f"'{entry['name']}' içe aktarılmış ama kullanılmıyor (satır {entry.get('line')})."))
                for entry in meta.get('imports', [])]
    if rule == 'unused-variable':
        function = meta.get('function', '')
        return [_base_item(finding, rule, project, (f"{function}:{entry['name']}", entry.get('line'),
                           f"'{entry['name']}' değişkeni {function or 'modül'} içinde atanıyor ama okunmuyor (satır {entry.get('line')})."))
                for entry in meta.get('variables', [])]
    line = source_evidence.line_of(finding)
    if rule == 'code-clone' and meta.get('locations'):
        line = meta['locations'][0].get('start_line')
    return [_base_item(finding, rule, project, (_discriminator(finding, rule, project), line, finding.description))]


def build_items(analysis: ProjectAnalysis) -> List[TaskItem]:
    """Görev olabilecek tüm öğeler (BİLGİ düzeyindekiler ve `SKIPPED_RULES` hariç), parmak izleriyle."""
    items: List[TaskItem] = []
    for finding in analysis.all_findings:
        rule = rule_of(finding)
        if finding.severity == Severity.INFO or rule in guide.SKIPPED_RULES:
            continue
        items.extend(_expand(finding, rule, analysis.project_path))
    seen: Counter = Counter()
    for item in sorted(items, key=lambda i: (i.key, i.line or 0)):         # aynı anahtarlar satır sırasıyla numaralanır
        item.fingerprint = _fingerprint(item.key, seen[item.key])
        seen[item.key] += 1
    return items


# ---- görev planı ---------------------------------------------------------------------------------------------------------

def _batches(items: List[TaskItem], size: int) -> Iterable[List[TaskItem]]:
    """Aynı dosyanın öğeleri aynı partide kalır; tek dosya `size`'ı aşarsa dosya bölünür."""
    by_file: Dict[str, List[TaskItem]] = defaultdict(list)
    for item in items:
        by_file[item.path].append(item)
    current: List[TaskItem] = []
    for path in sorted(by_file):
        group = sorted(by_file[path], key=lambda i: i.line or 0)
        for start in range(0, len(group), size):
            chunk = group[start:start + size]
            if current and len(current) + len(chunk) > size:
                yield current
                current = []
            current.extend(chunk)
    if current:
        yield current


def plan_tasks(items: List[TaskItem], batch_size: int = DEFAULT_BATCH_SIZE) -> List[Task]:
    """Dalga sırasına göre görevler: dalga -> kuralın en yüksek önceliği (azalan) -> kural adı."""
    if batch_size < 1:
        raise ValueError("batch_size en az 1 olmalı")
    groups: Dict[Tuple[int, str], List[TaskItem]] = defaultdict(list)
    for item in items:
        groups[(item.wave, item.rule)].append(item)
    top = {key: max(Severity[i.severity].value for i in members) for key, members in groups.items()}
    ordered = sorted(groups, key=lambda key: (key[0], -top[key], key[1]))
    tasks: List[Task] = []
    sequence: Counter = Counter()
    for wave, rule in ordered:
        members = groups[(wave, rule)]
        label = guide.label_of(rule, members[0].title.partition(': ')[0])
        for batch in _batches(members, batch_size):
            sequence[wave] += 1
            tasks.append(Task(f"W{wave}-{sequence[wave]:03d}", wave, rule, label, batch))
    return tasks


# ---- kapanış doğrulaması -----------------------------------------------------------------------------------------------

def _task_status(task: dict, current: Dict[str, TaskItem]) -> dict:
    """Bir görevin öğeleri için kapandı / azaldı / açık sayıları."""
    closed, reduced, still_open = [], [], []
    for entry in task['items']:
        now = current.get(entry['fingerprint'])
        if now is None:
            closed.append(entry['fingerprint'])
        elif now.count < entry.get('count', 1):
            reduced.append(entry['fingerprint'])
        else:
            still_open.append(entry['fingerprint'])
    return {'id': task['id'], 'wave': task['wave'], 'rule': task['rule'], 'total': len(task['items']),
            'closed': len(closed), 'reduced': len(reduced), 'open': len(still_open), 'open_fingerprints': still_open}


def _new_findings(current: Dict[str, TaskItem], recorded: dict) -> List[TaskItem]:
    known = {entry['fingerprint'] for task in recorded['tasks'] for entry in task['items']}
    return [item for fingerprint, item in current.items() if fingerprint not in known]


def verify(analysis: ProjectAnalysis, recorded: dict, only: Optional[Iterable[str]] = None) -> dict:
    """Kayıtlı görevlerdeki öğeler şimdi hâlâ var mı: kapandı / azaldı / açık, ayrıca yeni çıkan bulgular."""
    current = {item.fingerprint: item for item in build_items(analysis)}
    wanted = set(only) if only else {task['id'] for task in recorded['tasks']}
    report = [_task_status(task, current) for task in recorded['tasks'] if task['id'] in wanted]
    new = _new_findings(current, recorded)
    totals = {key: sum(row[key] for row in report) for key in ('total', 'closed', 'reduced', 'open')}
    return {'tasks': report, 'totals': totals, 'new_count': len(new),
            'new_findings': [{'fingerprint': i.fingerprint, 'rule': i.rule, 'severity': i.severity, 'path': i.path,
                              'line': i.line, 'title': i.title} for i in new[:MAX_NEW_REPORTED]]}
