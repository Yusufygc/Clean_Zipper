"""Denetim raporunun sabit verisi: öncelik simgeleri, boyut eşlemesi, kural etiketleri, efor / etki tabloları.

Rapor metni kural kimliğinden türetilir; bilinmeyen kural için genel varsayılanlar kullanılır.
"""
from typing import Dict, Tuple

from src.models.analysis_models import Severity

# öncelik -> (simge, ad)
SEVERITY_LABELS: Dict[Severity, Tuple[str, str]] = {
    Severity.CRITICAL: ('🔴', 'KRİTİK'),
    Severity.HIGH: ('🟠', 'YÜKSEK'),
    Severity.MEDIUM: ('🟡', 'ORTA'),
    Severity.LOW: ('🟢', 'DÜŞÜK'),
}

CATEGORY_NAMES: Dict[str, str] = {
    'security': 'Güvenlik', 'complexity': 'Karmaşıklık', 'duplicate': 'Tekrar', 'size': 'Boyut', 'structure': 'Yapı',
    'dependency': 'Bağımlılık', 'deadcode': 'Ölü kod', 'architecture': 'Mimari', 'reliability': 'Güvenilirlik',
    'testing': 'Test', 'hygiene': 'Proje hijyeni', 'git': 'Git geçmişi', 'type': 'Dosya türü',
}

# kategori -> V2 rapor boyutu
DIMENSIONS: Dict[str, str] = {
    'security': 'Güvenlik', 'dependency': 'Production', 'reliability': 'Production', 'hygiene': 'Production',
    'git': 'Production', 'testing': 'Test', 'architecture': 'Mimari',
}
DEFAULT_DIMENSION = 'Kod Kalitesi'

EFFORT_STEPS = ('S', 'M', 'L', 'XL')
EFFORT_TEXT = {'S': 'S (≤ 1 saat)', 'M': 'M (yarım gün)', 'L': 'L (1-3 gün)', 'XL': 'XL (hafta ve üstü)'}
DEFAULT_EFFORT = {Severity.CRITICAL: 'M', Severity.HIGH: 'M', Severity.MEDIUM: 'M', Severity.LOW: 'S'}

# tek bir bulgunun düzeltme eforu
RULE_EFFORT: Dict[str, str] = {
    'hardcoded-secret': 'S', 'provider-secret': 'S', 'secret-in-history': 'S', 'unused-import': 'S',
    'unused-variable': 'S', 'unreachable-code': 'S', 'magic-numbers': 'S', 'unused-dependency': 'S',
    'unpinned-dependencies': 'S', 'bare-except': 'S', 'swallowed-exception': 'S', 'empty-catch': 'S',
    'open-without-encoding': 'S', 'naive-datetime': 'S', 'print-density': 'S', 'test-sleep': 'S',
    'missing-readme': 'S', 'missing-license': 'S', 'missing-gitignore': 'S', 'missing-lockfile': 'S',
    'missing-env-example': 'S', 'missing-ci': 'M', 'function-metrics': 'M', 'module-imports': 'M', 'code-clone': 'M',
    'test-real-network': 'M', 'hotspot': 'M', 'class-size': 'L', 'file-length': 'L', 'import-cycle': 'L',
    'low-test-ratio': 'L', 'no-tests': 'XL',
}

RULE_LABELS: Dict[str, str] = {
    'function-metrics': 'Karmaşık / uzun işlevler', 'class-size': 'Aşırı büyük sınıflar', 'file-length': 'Aşırı uzun dosyalar',
    'module-imports': 'Çok fazla import', 'hardcoded-secret': 'Koda gömülü sır', 'provider-secret': 'Bilinen sağlayıcı anahtarı',
    'secret-in-history': 'Git geçmişinde sır dosyası', 'bare-except': 'Çıplak except', 'swallowed-exception': 'Yutulan hata',
    'empty-catch': 'Boş catch bloğu', 'open-without-encoding': 'Kodlamasız dosya açma', 'naive-datetime': 'Saat dilimsiz tarih',
    'print-density': 'Yoğun konsol çıktısı', 'unused-import': 'Kullanılmayan import', 'unused-variable': 'Kullanılmayan değişken',
    'unreachable-code': 'Ulaşılamaz kod', 'magic-numbers': 'Sihirli sayılar', 'code-clone': 'Kod klonları',
    'import-cycle': 'Döngüsel bağımlılık', 'unused-dependency': 'Kullanılmayan bağımlılık',
    'unpinned-dependencies': 'Sabitlenmemiş bağımlılık', 'no-tests': 'Test yok', 'low-test-ratio': 'Düşük test oranı',
    'test-sleep': 'Testte sleep', 'test-real-network': 'Testte gerçek ağ çağrısı', 'hotspot': 'Sık değişen karmaşık dosya',
    'missing-readme': 'README eksik', 'missing-license': 'LICENSE eksik', 'missing-gitignore': '.gitignore eksik',
    'missing-ci': 'CI yok', 'missing-lockfile': 'Kilit dosyası yok', 'missing-env-example': '.env.example eksik',
}

RULE_IMPACT: Dict[str, str] = {
    'function-metrics': 'Okunması ve test edilmesi zor kod; hata riski ve bakım maliyeti artar.',
    'class-size': 'Tek sınıfta çok sorumluluk (God Object); değişiklikler yan etki üretir.',
    'file-length': 'Büyük dosya gezinmeyi ve birleştirmeyi (merge) zorlaştırır.',
    'hardcoded-secret': 'Kaynak koda erişen herkes sırrı kullanabilir.',
    'provider-secret': 'Anahtar sızarsa üçüncü taraf hesabı kötüye kullanılabilir.',
    'secret-in-history': 'Dosya silinse de git geçmişinde okunabilir; sır ele geçmiş sayılmalı.',
    'swallowed-exception': 'Hatalar sessizce kaybolur; arıza teşhisi zorlaşır.',
    'bare-except': 'KeyboardInterrupt / SystemExit dahil her şey yakalanır; hata gizlenir.',
    'empty-catch': 'Hatalar sessizce kaybolur; arıza teşhisi zorlaşır.',
    'open-without-encoding': 'Platforma göre değişen kodlama (Windows cp1254) bozuk metne yol açar.',
    'naive-datetime': 'Saat dilimsiz tarih, sunucu / istemci farkında yanlış sonuç verir.',
    'unused-import': 'Gereksiz bağımlılık ve gürültü; başlangıç süresi uzar.',
    'unused-variable': 'Ölü kod okumayı yanıltır.',
    'unreachable-code': 'Hiç çalışmayacak kod yanıltıcıdır.',
    'magic-numbers': 'Anlamı belirsiz sabitler değiştirmeyi hataya açık yapar.',
    'code-clone': 'Aynı hata birden çok yerde düzeltilmek zorunda kalır.',
    'import-cycle': 'Modüller birbirinden ayrılamaz; test ve yeniden kullanım zorlaşır.',
    'unused-dependency': 'Gereksiz saldırı yüzeyi ve kurulum süresi.',
    'unpinned-dependencies': 'Kurulumlar tekrarlanamaz; sürüm değişimi sessizce kırabilir.',
    'no-tests': 'Değişikliklerin güvenle yapılabildiğine dair hiçbir kanıt yok.',
    'low-test-ratio': 'Test kapsamı düşük; gerilemeler fark edilmez.',
    'test-sleep': 'Kararsız (flaky) ve yavaş testler.',
    'test-real-network': 'Ağa bağlı kararsız testler.',
    'hotspot': 'Hataların yoğunlaştığı yer; önce burası iyileştirilmeli.',
    'missing-ci': 'Testler otomatik çalışmaz; kırık kod fark edilmeden birleşir.',
    'missing-license': 'Lisanssız kod varsayılan olarak başkalarınca kullanılamaz.',
    'missing-lockfile': 'Bağımlılık sürümleri sabit değil; kurulumlar tekrarlanamaz.',
}
CATEGORY_IMPACT: Dict[str, str] = {
    'security': 'Sömürülebilir bir güvenlik zayıflığı oluşturabilir.',
    'reliability': 'Hataların fark edilmesini ve üretimde teşhisini zorlaştırır.',
    'testing': 'Değişikliklerin güvenle yapılabilmesini engeller.',
    'duplicate': 'Aynı içerik birden çok yerde bakım gerektirir; depolama israfı.',
    'hygiene': 'Projenin sürdürülebilirliğini ve devrini zorlaştırır.',
}
DEFAULT_IMPACT = 'Kalite ve bakım maliyetini olumsuz etkiler.'

RULE_DEPENDENCY: Dict[str, str] = {
    'secret-in-history': 'Önce anahtarların döndürülmesi, sonra geçmiş temizliği (git filter-repo / BFG)',
    'hardcoded-secret': 'Anahtarın döndürülmesi ve ortam değişkeni altyapısı',
    'provider-secret': 'Anahtarın sağlayıcıda döndürülmesi',
    'import-cycle': 'Ortak kodu ayıracak yeni modülün tasarımı',
    'no-tests': 'Test çatısının (pytest / jest ...) seçimi',
    'missing-ci': 'Çalışan bir test komutu',
}
RULE_RISK: Dict[str, str] = {
    'secret-in-history': 'Geçmiş yeniden yazılırsa tüm klonlar yeniden alınmalı',
    'import-cycle': 'Orta: taşıma sırasında davranış değişebilir',
    'function-metrics': 'Orta: testsiz refactor davranışı bozabilir',
    'class-size': 'Orta: bölme çağıranları etkiler',
    'swallowed-exception': 'Düşük: ama gizli hatalar görünür hale gelir',
}
DEFAULT_RISK = 'Düşük'

# "iyi pratikler" bölümünde gösterilecek hijyen maddeleri
HYGIENE_GOOD = {
    'readme': 'README var', 'license': 'LICENSE var', 'gitignore': 'Kök .gitignore var',
    'ci': 'CI yapılandırması var', 'lockfile': 'Kilit dosyaları mevcut (tekrarlanabilir kurulum)',
    'env-example': '.env.example mevcut', 'dockerfile': 'Dockerfile mevcut',
}

SKIP_REASONS = {
    'too_large': 'Çok büyük dosya (2 MB üstü), içerik taranmadı',
    'unreadable': 'Okunamayan dosya (izin / kodlama)',
    'parse_error': 'Sözdizimi hatası nedeniyle ayrıştırılamayan dosya',
    'minified': 'Minify edilmiş (okunamaz) dosya, yapı analizi atlandı',
    'unreadable_dir': 'Erişilemeyen klasör',
}

# kanıt olarak kod parçası YAZILMAYACAK kurallar (sır içerebilir)
NO_EVIDENCE_RULES = frozenset({'hardcoded-secret', 'provider-secret', 'secret-in-history'})


def effort_of(rule: str, severity: Severity, count: int = 1) -> str:
    """Tek bulgu için tablo değeri; `count` büyüdükçe bir ya da iki basamak yükselir."""
    base = RULE_EFFORT.get(rule) or DEFAULT_EFFORT.get(severity, 'M')
    step = EFFORT_STEPS.index(base) + (2 if count > 20 else 1 if count > 3 else 0)
    return EFFORT_STEPS[min(step, len(EFFORT_STEPS) - 1)]


def badge(severity: Severity) -> str:
    icon, name = SEVERITY_LABELS[severity]
    return f"{icon} {name}"


def dimension(category: str) -> str:
    return DIMENSIONS.get(category, DEFAULT_DIMENSION)


def impact_of(rule: str, category: str) -> str:
    return RULE_IMPACT.get(rule) or CATEGORY_IMPACT.get(category, DEFAULT_IMPACT)
