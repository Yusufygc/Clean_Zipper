"""Denetim raporu için bulgunun konumu ve kanıt (kod parçası) bilgisi."""
from itertools import islice
from pathlib import Path
from typing import Optional

from src.core.path_rules import secret_kind
from src.models.analysis_models import AnalysisResult
from src.services import audit_catalog as catalog

EVIDENCE_LINES = 3
EVIDENCE_WIDTH = 160
EVIDENCE_MAX_BYTES = 2 * 1024 * 1024


def relative(project: Path, path: Optional[Path]) -> str:
    """Proje köküne göre, '/' ayraçlı yol; köke ait değilse olduğu gibi."""
    if path is None:
        return '-'
    try:
        shown = Path(path).relative_to(project)
    except ValueError:
        return Path(path).as_posix()
    return shown.as_posix() or '.'


def line_of(finding: AnalysisResult) -> Optional[int]:
    """Bulgunun ilk satırı (`line`, `start_line` ya da `lines[0]` metadata'sından)."""
    meta = finding.metadata
    for key in ('line', 'start_line'):
        if isinstance(meta.get(key), int):
            return meta[key]
    lines = meta.get('lines')
    if isinstance(lines, list) and lines and isinstance(lines[0], int):
        return lines[0]
    return None


def _may_show_source(finding: AnalysisResult) -> bool:
    """Sır içerebilecek bulguların ya da dosyaların içeriği rapora asla yazılmaz."""
    path = finding.file_path
    if path is None or finding.metadata.get('rule') in catalog.NO_EVIDENCE_RULES:
        return False
    return finding.metadata.get('kind') != 'sensitive_file' and not secret_kind(Path(path).name)


def evidence(finding: AnalysisResult, line: Optional[int]) -> Optional[str]:
    """Bulgunun bulunduğu satırdan başlayan birkaç satır (numaralı); yazılamıyorsa None."""
    if not line or not _may_show_source(finding):
        return None
    return snippet(Path(finding.file_path), line)


def snippet(path: Path, line: int) -> Optional[str]:
    """`path` dosyasının `line` satırından başlayan numaralı birkaç satırı; okunamıyorsa ya da büyükse None.
    Sır denetimi çağıranın işidir (`evidence` yapar)."""
    if not line or line < 1:
        return None
    try:
        if not path.is_file() or path.stat().st_size > EVIDENCE_MAX_BYTES:
            return None
        with open(path, encoding='utf-8', errors='replace') as handle:
            window = [text.rstrip('\r\n') for text in islice(handle, line - 1, line - 1 + EVIDENCE_LINES)]
    except OSError:
        return None
    return '\n'.join(f"{line + i}: {text[:EVIDENCE_WIDTH]}" for i, text in enumerate(window)) or None
