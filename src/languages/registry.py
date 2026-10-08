"""Dil kayıt defteri ve dosya başına önbellekli çözümleme girişi."""
import fnmatch
import logging
from typing import Dict, Optional

from src.core.project_index import FileEntry, ProjectIndex
from src.languages.base import LanguageSupport, SourceMetrics

logger = logging.getLogger(__name__)

# Üretilmiş / küçültülmüş dosyalar ölçüme girmez (küçük harfli dosya adına uygulanır).
GENERATED_FILE_PATTERNS = (
    '*.min.*', '*.d.ts', '*.g.cs', '*.designer.cs', '*.generated.*',
    '*.pb.go', '*_pb2.py', '*_pb2_grpc.py', '*_ui.py', '*_rc.py',
)

MEMO_NAMESPACE = 'source_metrics'


class LanguageRegistry:
    def __init__(self):
        self._by_id: Dict[str, LanguageSupport] = {}
        self._by_extension: Dict[str, LanguageSupport] = {}

    def register(self, language: LanguageSupport) -> LanguageSupport:
        self._by_id[language.id] = language
        for ext in language.extensions:
            self._by_extension[ext.lower()] = language
        return language

    def get(self, language_id: str) -> Optional[LanguageSupport]:
        return self._by_id.get(language_id)

    def for_extension(self, ext: str) -> Optional[LanguageSupport]:
        return self._by_extension.get(ext.lower())

    def ids(self):
        return sorted(self._by_id)


default_languages = LanguageRegistry()


def is_generated(file_name: str) -> bool:
    name = file_name.lower()
    return any(fnmatch.fnmatch(name, pattern) for pattern in GENERATED_FILE_PATTERNS)


# Küçültülmüş / paketlenmiş dosyalar adından anlaşılmaz (ör. webpack parçaları): satır uzunluğuna bakılır.
MINIFIED_LONGEST_LINE = 5000
MINIFIED_AVERAGE_LINE = 300


def looks_minified(text: str) -> bool:
    lines = text.split('\n')
    if len(text) < MINIFIED_LONGEST_LINE:
        return False
    return max(map(len, lines)) > MINIFIED_LONGEST_LINE or len(text) / max(len(lines), 1) > MINIFIED_AVERAGE_LINE


def parse_file(index: ProjectIndex, entry: FileEntry,
               registry: LanguageRegistry = default_languages) -> Optional[SourceMetrics]:
    """Dosyanın ölçümlerini döner; desteklenmeyen, üretilmiş, ikilik veya çözümlenemeyen dosyada None.

    Sonuç indekste önbelleğe alınır; aynı dosyayı birden çok analizör ister.
    """
    language = registry.for_extension(entry.ext)
    if language is None or is_generated(entry.path.name):
        return None
    return index.memo(MEMO_NAMESPACE, entry, lambda: _analyze(index, entry, language, registry))


def _analyze(index: ProjectIndex, entry: FileEntry, language: LanguageSupport,
             registry: LanguageRegistry) -> Optional[SourceMetrics]:
    text = index.read_text(entry)
    if text is None or looks_minified(text):
        return None
    language = registry.get(language.refine(text)) or language
    try:
        return language.analyze(text)
    except Exception:
        logger.warning("Dosya çözümlenemedi, atlandı: %s (%s)", entry.rel, language.id, exc_info=True)
        return None
