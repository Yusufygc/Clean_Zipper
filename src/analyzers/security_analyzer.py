import re
from bisect import bisect_right
from pathlib import Path
from typing import List, Optional
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity
from src.utils.gitignore_parser import GitignoreMatcher

SENSITIVE_FILE_NAMES = frozenset({'.env', 'credentials.json', 'secrets.yaml'})

# Biçimi bilinen sağlayıcı sırları (kalıplar parçalanır: kendi kaynağımız yanlışlıkla eşleşmesin).
# Her kalıbın `hints` alanı: metinde bulunması gereken sabit parçalar. Hızlı alt dize araması, pahalı regex'i
# (284 MB'lık gerçek korpusta kalıp başına ~4 sn) yalnızca olası dosyalarda çalıştırır.
PROVIDER_SECRETS = (
    ('AWS erişim anahtarı', re.compile(r'\b(?:AK' + r'IA|AS' + r'IA)[0-9A-Z]{16}\b'), Severity.CRITICAL, ('AK' + 'IA', 'AS' + 'IA')),
    ('Özel anahtar (PEM)', re.compile(r'-----BEGIN (?:[A-Z]+ )?PRIV' + r'ATE KEY(?: BLOCK)?-----'), Severity.CRITICAL, ('-----BEGIN',)),
    ('GitHub token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b'), Severity.CRITICAL,
     ('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_', 'github_pat_')),
    ('Slack token', re.compile(r'\bxox[abprs]-[A-Za-z0-9-]{10,}\b'), Severity.HIGH, ('xox',)),
    ('Google API anahtarı', re.compile(r'\bAI' + r'za[0-9A-Za-z_\-]{35}\b'), Severity.HIGH, ('AI' + 'za',)),
    ('Stripe canlı anahtar', re.compile(r'\b[sr]k_li' + r've_[0-9a-zA-Z]{24,}\b'), Severity.CRITICAL, ('_li' + 've_',)),
    ('JWT', re.compile(r'\bey' + r'J[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'), Severity.HIGH, ('ey' + 'J',)),
)

# Genel sızıntılar iki adımdır: ucuz bir "çapa" (sabit karakterle başlar, regex motoru hızlı tarar) ve eşleşmenin
# hemen öncesindeki anahtar sözcük denetimi. Anlamı `(key|secret|...)\s*=\s*'değer'` ile aynıdır.
_ASSIGNED_LITERAL = re.compile(r'=[^\S\n]*[\'"][A-Za-z0-9_\-]{8,}[\'"]')
_SECRET_WORD_BEFORE = re.compile(r'(?:key|secret|password|passwd|token)[^\S\n]*\Z', re.IGNORECASE)
_DB_SCHEME = re.compile(r'://')
# Kendi kodumuzu yanlışlıkla sızıntı olarak işaretlememesi (False Positive) için dizeler parçalanır.
_DB_NAME_BEFORE = re.compile(r'(?:mongo' + r'db(?:\+srv)?|post' + r'gres|my' + r'sql)\Z', re.IGNORECASE)
GENERIC_SECRETS = (
    ("API Anahtarı / Şifre", _ASSIGNED_LITERAL, _SECRET_WORD_BEFORE, 40),
    ("Veritabanı URL Sızıntısı", _DB_SCHEME, _DB_NAME_BEFORE, 16),
)

class _Lines:
    """Metindeki satır numaralarını yalnızca ilk eşleşmede (tembel) hesaplayıp önbelleğe alır."""

    def __init__(self, text: str):
        self._text = text
        self._starts: Optional[List[int]] = None

    def _line_starts(self) -> List[int]:
        if self._starts is None:
            self._starts = [0] + [m.end() for m in re.finditer('\n', self._text)]
        return self._starts

    def number(self, offset: int) -> int:
        return bisect_right(self._line_starts(), offset)

    def text(self, number: int) -> str:
        starts = self._line_starts()
        end = starts[number] - 1 if number < len(starts) else len(self._text)
        return self._text[starts[number - 1]:end]


@register_analyzer
class SecurityLeakAnalyzer(BaseAnalyzer):
    def __init__(self, priority: int = 15):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Güvenlik Sızıntısı Analizörü"

    @property
    def category(self) -> str:
        return "security"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        tracked = index.git_tracked          # None: git yok / depo değil (izleme bilinmiyor)

        for entry in index.files:
            file_path = entry.path

            # Riskli dosya adı (.env veya credentials kontrolü)
            if file_path.name in SENSITIVE_FILE_NAMES:
                results.append(self._sensitive_file_result(index, entry.rel, file_path, tracked))
                continue

            # Kod içi tarama mantığı (ikilik ve çok büyük dosyalar atlanır)
            text = index.read_text(entry)
            if text is not None:
                results.extend(self._scan_text(text, file_path))

        results.extend(self._tracked_but_ignored(index, tracked))
        return results

    def _scan_text(self, text: str, file_path) -> List[AnalysisResult]:
        """Tüm metin üzerinde tek geçiş (satır satır döngüden çok daha hızlı); kalıplar satır sınırını aşmaz."""
        lines = _Lines(text)
        return self._generic_secrets(text, lines, file_path) + self._provider_secrets(text, lines, file_path)

    def _generic_secrets(self, text: str, lines: '_Lines', file_path) -> List[AnalysisResult]:
        results = []
        for pattern_name, anchor, before, window in GENERIC_SECRETS:
            for match in anchor.finditer(text):
                if not before.search(text, max(0, match.start() - window), match.start()):
                    continue
                line_num = lines.number(match.start())
                results.append(self._create_result(
                    title=f"Açık Şifreleme/Key Sızıntısı ({file_path.name})",
                    description=f"Satır {line_num}: Kod içinde sertifikasız '{pattern_name}' algılandı.",
                    severity=Severity.HIGH,
                    file_path=file_path,
                    recommendation="Şifre ve anahtarları doğrudan kod içine yazmak yerine çevre değişkenlerinden (.env) çağırın.",
                    rule='hardcoded-secret', line=line_num,
                ))
        return results

    def _provider_secrets(self, text: str, lines: '_Lines', file_path) -> List[AnalysisResult]:
        """Biçimi bilinen sağlayıcı anahtarları. Değer asla bulguya yazılmaz; yalnızca maskeli önek."""
        results = []
        for provider, regex, severity, hints in PROVIDER_SECRETS:
            if not any(hint in text for hint in hints):
                continue
            for match in regex.finditer(text):
                line_num = lines.number(match.start())
                if 'example' in lines.text(line_num).lower():
                    continue                                 # belge / örnek anahtarlar (ör. AKIA...EXAMPLE)
                value = match.group(0)
                results.append(self._create_result(
                    title=f"Sızan {provider} ({file_path.name})",
                    description=f"Satır {line_num}: {provider} biçiminde bir değer algılandı ({value[:4]}… {len(value)} karakter).",
                    severity=severity, file_path=file_path,
                    recommendation="Değeri hemen iptal edip yenileyin (rotate), koddan çıkarıp ortam değişkeni veya gizli yönetim servisine taşıyın; geçmişte kaldıysa geçmişi temizleyin.",
                    rule='provider-secret', provider=provider, line=line_num,
                ))
        return results

    def _sensitive_file_result(self, index: ProjectIndex, rel: str, file_path, tracked) -> AnalysisResult:
        """İndekste kalan hassas dosya: git'e commit edilmiş mi, yoksa yalnızca .gitignore'a eklenmemiş mi."""
        tracking_known = tracked is not None
        if tracking_known and rel in tracked:
            # İzlenen dosya kurala uysa bile indekste kalır; "zaten .gitignore'da" bilgisini kurallardan öğren.
            matches_rules = GitignoreMatcher(str(index.root)).is_ignored(file_path)
            return self._committed_result(rel, file_path, ignored=matches_rules)
        note = "" if tracking_known else " (git bilgisi alınamadı: dosyanın zaten commit edilip edilmediği bilinmiyor)"
        return self._create_result(
            title=f"Kritik Güvenlik Riski: {file_path.name}",
            description=f"'{rel}' hassas yapılandırma dosyası .gitignore'a eklenmemiş; commit edilme riski var.{note}",
            severity=Severity.CRITICAL,
            file_path=file_path,
            recommendation="Bu dosyayı hemen .gitignore içerisine ekleyin ve sunucuda ortam değişkeni (env) olarak tanımlayın.",
            kind='sensitive_file', committed=False, tracking_known=tracking_known,
        )

    def _committed_result(self, rel: str, file_path, ignored: bool) -> AnalysisResult:
        reason = " ve .gitignore'da olmasına rağmen" if ignored else ""
        return self._create_result(
            title=f"Kritik Güvenlik Riski: {file_path.name} git'e commit edilmiş",
            description=(f"'{rel}' hassas dosyası git tarafından izleniyor{reason}. "
                         ".gitignore izlenen dosyayı depodan ve geçmişten silmez; içindeki sırlar ele geçmiş sayılmalı."),
            severity=Severity.CRITICAL,
            file_path=file_path,
            recommendation=(f"'git rm --cached {rel}' ile izlemeden çıkarın, içindeki sırları değiştirin (rotate) "
                            "ve gerekirse geçmişi temizleyin."),
            kind='sensitive_file', committed=True, tracking_known=True, gitignored=ignored,
        )

    def _tracked_but_ignored(self, index: ProjectIndex, tracked) -> List[AnalysisResult]:
        """.gitignore'a eklenmiş ama git'in hâlâ izlediği hassas dosyalar (indekste yoklar; git'ten bulunur)."""
        if not tracked:
            return []
        in_index = {f.rel for f in index.files}
        return [
            self._committed_result(rel, index.root / rel, ignored=True)
            for rel in sorted(tracked)
            if rel.rsplit('/', 1)[-1] in SENSITIVE_FILE_NAMES and rel not in in_index
        ]
