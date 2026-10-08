"""Ajan görevleri için sabit veri: dalgalar, kural -> dalga eşlemesi ve kural başına "nasıl düzelt / neleri yapma" metinleri.

Dalga sırası bilinçlidir: testler (5) refactor'dan (6) önce gelir; sır ve karar gerektiren işler (0) ajana bırakılmaz.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.services import audit_catalog as catalog


@dataclass(frozen=True)
class Guidance:
    how: str                    # nasıl düzeltilir
    avoid: str                  # neleri yapma
    risk: str                   # 'düşük' | 'orta' | 'yüksek'
    commit: str = 'refactor'    # commit tipi önerisi


# dalga -> (ad, kim yapar)
WAVES: Dict[int, Tuple[str, str]] = {
    0: ('İnsan aksiyonu', 'insan'),
    1: ('Güvenlik', 'ajan (dikkatli)'),
    2: ('Güvenilirlik', 'ajan'),
    3: ('Mekanik temizlik', 'ajan (düşük risk)'),
    4: ('Bağımlılık ve hijyen', 'ajan'),
    5: ('Test', 'ajan (refactor öncesi)'),
    6: ('Refactor', 'ajan (testler geçmeli)'),
}

HUMAN_WAVE = 0

# Görev olmayan kurallar (yalnızca bilgi / başka görevlere not).
SKIPPED_RULES = frozenset({'hotspot', 'co-change', 'todo-inventory', 'clone-summary', 'dependency-graph',
                           'hygiene-summary', 'test-summary', 'untested-modules'})

RULE_WAVE: Dict[str, int] = {
    'hardcoded-secret': 0, 'provider-secret': 0, 'secret-in-history': 0, 'sensitive-file': 0, 'tracked-artifacts': 0,
    'missing-license': 0,
    'bare-except': 2, 'swallowed-exception': 2, 'empty-catch': 2, 'open-without-encoding': 2, 'debug-flag': 2,
    'debugger-statement': 2,
    'unused-import': 3, 'unused-variable': 3, 'unreachable-code': 3, 'magic-numbers': 3, 'print-density': 3,
    'naive-datetime': 3,
    'unpinned-dependencies': 4, 'dev-dependency-in-runtime': 4, 'unused-dependency': 4, 'missing-readme': 4,
    'missing-gitignore': 4, 'missing-ci': 4, 'missing-lockfile': 4, 'missing-env-example': 4, 'large-file': 4,
    'duplicate-files': 4, 'empty-folder': 4,
    'no-tests': 5, 'low-test-ratio': 5, 'test-sleep': 5, 'test-real-network': 5,
    'function-metrics': 6, 'class-size': 6, 'file-length': 6, 'module-imports': 6, 'code-clone': 6, 'import-cycle': 6,
}
CATEGORY_WAVE: Dict[str, int] = {
    'security': 1, 'reliability': 2, 'deadcode': 3, 'dependency': 4, 'hygiene': 4, 'size': 4, 'type': 4, 'structure': 4,
    'testing': 5, 'complexity': 6, 'duplicate': 6, 'architecture': 6,
}
DEFAULT_WAVE = 6

GUIDANCE: Dict[str, Guidance] = {
    # ---- dalga 0: insan ---------------------------------------------------------------------------------------
    'hardcoded-secret': Guidance(
        "İNSAN AKSİYONU. Değer gerçek bir sırsa sağlayıcıda geçersiz kıl ve yenile (rotate); sonra koddan çıkarıp ortam değişkenine / secret yöneticisine taşı. Değer sahte test verisiyse bulgu yanlış pozitiftir.",
        "Ajan sır değerini okuma, kopyalama, loga ya da commit mesajına yazma. Değeri başka bir dosyaya taşıma.", 'yüksek', 'fix'),
    'provider-secret': Guidance(
        "İNSAN AKSİYONU. Anahtarı sağlayıcının panelinde hemen iptal et ve yenile; yenisini koda değil ortam değişkenine / secret yöneticisine koy. Geçmişte kaldıysa geçmiş temizliği düşün.",
        "Ajan anahtarı okuma, kopyalama, loga yazma.", 'yüksek', 'fix'),
    'secret-in-history': Guidance(
        "İNSAN AKSİYONU. Geçmişte commit edilmiş dosyadaki sırları geçersiz kıl ve yenile. Geçmişten silmek gerekirse `git filter-repo` ya da BFG kullanılır; bu geçmişi yeniden yazar ve herkesin klonunu etkiler.",
        "Ajan geçmişi yeniden yazma (force push, filter-repo) çalıştırma.", 'yüksek', 'fix'),
    'sensitive-file': Guidance(
        "İNSAN AKSİYONU. Hassas dosyayı `.gitignore`'a ekle, izleniyorsa `git rm --cached <dosya>` ile izlemeden çıkar, içindeki sırları yenile.",
        "Dosyanın içeriğini okuma ya da kopyalama.", 'yüksek', 'fix'),
    'tracked-artifacts': Guidance(
        "İNSAN ONAYI. Üretilmiş içeriği `git rm -r --cached <kök>` ile izlemeden çıkar ve `.gitignore`'a ekle (dosyalar diskte kalır; geçmiş değişmez). `dist`/`build` bulgusunda klasörün gerçekten üretilmiş içerik olduğunu doğrula.",
        "Klasörü diskten silme; `lib/`, `vendor/` altındaki bilinçli üçüncü taraf paketlerine dokunma.", 'orta', 'chore'),
    'missing-license': Guidance(
        "İNSAN KARARI. Lisans türünü proje sahibi seçer (MIT, Apache-2.0, ticari ...). Seçim yapıldıktan sonra LICENSE dosyasını ekle.",
        "Sahibine sormadan lisans seçme.", 'düşük', 'docs'),
    # ---- dalga 2: güvenilirlik --------------------------------------------------------------------------------
    'bare-except': Guidance(
        "`except:` yerine beklenen istisna türlerini yaz (örn. `except (OSError, ValueError):`). Gerçekten her şeyi yakalaman gerekiyorsa `except Exception:` kullan, hatayı logla ve gerekiyorsa yeniden fırlat.",
        "KeyboardInterrupt / SystemExit'i yutma. Hatayı `pass` ile geçiştirme.", 'orta', 'fix'),
    'swallowed-exception': Guidance(
        "Yutulan hatayı logla (`logger.exception` / `logger.warning`) ya da daha dar bir istisna türü yakala. Bilinçli yutma ise nedenini açıklayan bir yorum bırak (araç, yorumla gerekçelendirilmiş yutmayı bulgu saymaz).",
        "Hatayı dışarı fırlatarak davranışı değiştirme: çağıranlar yutmaya güveniyor olabilir, önce çağıranlara bak.", 'orta', 'fix'),
    'empty-catch': Guidance(
        "Boş `catch` bloğuna hata günlüğü ekle ya da hatayı yeniden fırlat. Bilinçli yutma ise nedenini yorumla belirt.",
        "Boş bloğu başka bir sessiz davranışla (`return null` gibi) değiştirme.", 'orta', 'fix'),
    'open-without-encoding': Guidance(
        "Metin modunda açılan dosyalara `encoding='utf-8'` ekle (`open(...)`, `Path.read_text()`, `write_text()`). İkili modda (`'rb'`, `'wb'`) dokunma.",
        "Dosya gerçekte başka bir kodlamadaysa (cp1254 vb.) körü körüne utf-8 yazma; mevcut dosyayı okuyup doğrula.", 'orta', 'fix'),
    'debug-flag': Guidance(
        "Sabit `DEBUG = True` değerini ortam değişkenine bağla (örn. `os.environ.get('APP_DEBUG') == '1'`), varsayılan `False` olsun.",
        "Geliştirme ortamının çalışma biçimini bozma; README'ye yeni değişkeni yaz.", 'orta', 'fix'),
    'debugger-statement': Guidance("`debugger` / `breakpoint()` ifadelerini sil.", "Yanındaki mantığa dokunma.", 'düşük', 'chore'),
    # ---- dalga 3: mekanik temizlik ------------------------------------------------------------------------------
    'unused-import': Guidance(
        "Listelenen kullanılmayan import'ları sil. Yan etki için bilerek yapılan import'ta (eklenti kaydı vb.) silme; nedenini yorumla ve `# noqa: F401` ekle.",
        "`__init__.py` içindeki yeniden dışa aktarımları ve `__all__` öğelerini silme. `TYPE_CHECKING` bloğundaki tip import'larını kullanımı doğrulamadan silme.", 'düşük', 'refactor'),
    'unused-variable': Guidance(
        "Atamanın sağ tarafında yan etki yoksa değişkeni sil. Yan etki varsa (fonksiyon çağrısı) yalnızca atamayı kaldırıp çağrıyı bırak.",
        "Tuple açmadaki (`a, b = f()`) kullanılmayan elemanı silme, `_` ile adlandır.", 'düşük', 'refactor'),
    'unreachable-code': Guidance(
        "`return` / `raise` / `break` / `continue` sonrasındaki ulaşılamaz ifadeleri sil. Önce neden ulaşılamaz olduğunu anla: asıl niyet farklıysa (yanlış yerleştirilmiş `return`) mantığı düzelt.",
        "Sırf silmek için silme; `return`'ün yanlış yerde olup olmadığını kontrol et.", 'orta', 'fix'),
    'magic-numbers': Guidance(
        "Anlamı olan sayıları adlandırılmış sabitlere çıkar (modül başında BÜYÜK_HARF); aynı sayı birden çok yerdeyse tek sabit.",
        "0, 1, -1, 2 gibi açık sayıları, indeksleri ve dizi / enum başlatıcılarını sabite çıkarma. Arayüz piksel / renk değerlerini yalnızca anlam taşıyorsa çıkar.", 'düşük', 'refactor'),
    'print-density': Guidance(
        "Kalıcı çıktı olması gereken `print` / `console.log` çağrılarını günlükleme ile değiştir (`logger = logging.getLogger(__name__)`), uygun seviyeyi seç.",
        "`if __name__ == '__main__'` altındaki ve bilinçli komut satırı çıktısını değiştirme.", 'düşük', 'refactor'),
    'naive-datetime': Guidance(
        "`datetime.now()` yerine `datetime.now(timezone.utc)`, `utcnow()` yerine `now(timezone.utc)` kullan. Karşılaştırdığın diğer tarih değerlerinin de saat dilimli olduğundan emin ol.",
        "Saat dilimli ve saatsiz değerleri karıştırma (`TypeError`). Kullanıcıya yerel saat gösteriliyorsa `.astimezone()` ile çevir, UTC göstererek bozma.", 'orta', 'fix'),
    # ---- dalga 4: bağımlılık ve hijyen --------------------------------------------------------------------------------
    'unpinned-dependencies': Guidance(
        "Listelenen bağımlılıkları ortamda kurulu ve testlerin geçtiği sürüme sabitle (`paket==X.Y.Z`; npm'de `^` / `~` yerine tam sürüm ya da kilit dosyası).",
        "Sürümü tahmin etme; yalnızca gerçekten kurulu sürümü yaz. Kurulu sürümü öğrenemiyorsan görevi atla ve bildir.", 'orta', 'chore'),
    'dev-dependency-in-runtime': Guidance(
        "Test / paketleme araçlarını `requirements-dev.txt` ve `requirements-build.txt` gibi ayrı dosyalara taşı (her biri `-r requirements.txt` ile başlasın) ve README kurulum komutlarını güncelle.",
        "Araçların sürümlerini değiştirme.", 'düşük', 'chore'),
    'unused-dependency': Guidance(
        "Gerçekten kullanılmıyorsa manifest'ten sil.",
        "Dinamik içe aktarma (`importlib`), eklenti sistemi, komut satırı aracı olarak kullanım ve `types-*` paketleri yanlış pozitif olabilir: silmeden önce projede ara.", 'orta', 'chore'),
    'missing-readme': Guidance(
        "Projeyi, kurulumu ve kullanımı anlatan bir `README.md` yaz; içeriği koddan ve mevcut dosyalardan çıkar.",
        "Doğrulayamadığın özellik ya da komut yazma.", 'düşük', 'docs'),
    'missing-gitignore': Guidance(
        "Projenin diline uygun kök `.gitignore` oluştur (sanal ortam, `node_modules`, derleme çıktıları, `.env`).",
        "Zaten izlenen dosyaları silme; izlemeden çıkarma ayrı bir karardır.", 'düşük', 'chore'),
    'missing-ci': Guidance(
        "Testleri her değişiklikte çalıştıran basit bir CI iş akışı ekle (örn. `.github/workflows/test.yml`); projenin gerçek test komutunu kullan.",
        "Dağıtım / yayın adımları ekleme; gizli anahtar gerektiren iş akışı yazma.", 'orta', 'chore'),
    'missing-lockfile': Guidance(
        "Paket yöneticisiyle kilit dosyasını üret (`npm install`, `poetry lock`, `cargo build`, `go mod tidy`) ve ekle.",
        "Ağ erişimin yoksa görevi atla ve bildir; kilit dosyasını elle yazma.", 'orta', 'chore'),
    'missing-env-example': Guidance(
        "`.env` dosyasındaki anahtar ADLARINI boş değerlerle `.env.example` olarak kaydet.",
        "`.env` içindeki DEĞERLERİ kopyalama.", 'düşük', 'docs'),
    'large-file': Guidance(
        "Dosyanın gerekli olup olmadığını belirle: derleme çıktısı ya da veri ise `.gitignore`'a / Git LFS'e değerlendir, kaynak dosyaysa böl.",
        "Kullanıcıya sormadan silme.", 'orta', 'chore'),
    'duplicate-files': Guidance(
        "Aynı içerikli dosyalardan asıl olanı belirle; kopyaları tek kaynağa referansla değiştir.",
        "Kullanıcıya sormadan dosya silme.", 'orta', 'chore'),
    'empty-folder': Guidance(
        "Bilinçli yer tutucuysa `.gitkeep` ekle, değilse sil.", "Klasörün başka bir araç tarafından oluşturulduğunu doğrula.", 'düşük', 'chore'),
    # ---- dalga 5: test ----------------------------------------------------------------------------------------------
    'no-tests': Guidance(
        "En değerli birkaç modül için birim testi yaz; önce saf fonksiyonlardan başla. Test çatısı yoksa kur ve geliştirme bağımlılıklarına ekle.",
        "Mevcut davranışı değiştirme; testi geçirmek için kodu bozma. Gerçek ağ / dosya sistemi bağımlılıklarını sahtele.", 'orta', 'test'),
    'low-test-ratio': Guidance(
        "Test kapsamı en zayıf modüllere öncelik vererek testler ekle (özellikle sonraki dalgada refactor edilecek dosyalar).",
        "Anlamsız testlerle sayıyı şişirme.", 'orta', 'test'),
    'test-sleep': Guidance(
        "Testlerdeki gerçek `sleep` çağrılarını zamanı sahteleyerek ya da koşul bekleyen bir yardımcıyla değiştir.",
        "Zaman aşımını kaldırıp testi sonsuza kadar bekleyebilir hale getirme.", 'düşük', 'test'),
    'test-real-network': Guidance(
        "Dış ağ çağrılarını mock ya da yerel sahte sunucu ile değiştir.", "Testin doğruladığı davranışı zayıflatma.", 'düşük', 'test'),
    # ---- dalga 6: refactor --------------------------------------------------------------------------------------------
    'function-metrics': Guidance(
        "Fonksiyonu tek sorumluluğa sahip küçük fonksiyonlara böl (Extract Method), iç içe koşulları erken dönüşle düzleştir, parametre grubunu bir nesneye topla. Önce bu fonksiyonu kapsayan test var mı bak; yoksa önce karakterizasyon testi yaz.",
        "Davranışı, imzayı ve dönüş değerini değiştirme. Aynı turda birden fazla fonksiyonu refactor etme.", 'orta', 'refactor'),
    'class-size': Guidance(
        "Sınıfı sorumluluklara göre böl (yardımcı sınıf çıkar, kompozisyon kullan). Genel arayüzü koru.",
        "Çağıranları kırma; taşıdığın üyeler için eski adı delege eden ince bir katman bırak. Testsiz yapma.", 'yüksek', 'refactor'),
    'file-length': Guidance(
        "Dosyayı mantıksal modüllere böl; eski dosyadan yeniden dışa aktarımla geriye uyumluluğu koru.",
        "Döngüsel içe aktarma yaratma. Testsiz yapma.", 'yüksek', 'refactor'),
    'module-imports': Guidance(
        "Çok sayıda import çoğunlukla modülün çok sorumluluğu olduğunu gösterir; sorumluluğa göre böl. Küçük adım: kullanılmayanları temizle.",
        "Yalnızca import sayısını düşürmek için importları fonksiyon içine taşıma.", 'orta', 'refactor'),
    'code-clone': Guidance(
        "Ortak bloğu tek bir fonksiyona çıkar ve kopyaların yerine çağır.",
        "Kopyalar küçük farklar taşıyorsa (parametre) farkı parametreleştir; davranışı değiştirme.", 'orta', 'refactor'),
    'import-cycle': Guidance(
        "Döngüyü ortak kodu üçüncü bir modüle çıkararak kır ya da bağımlılığı tersine çevir (arayüz / geri çağırma). Son çare: içe aktarmayı fonksiyon içine al.",
        "Önce testlerin geçtiğini doğrula; taşıma sırasında genel arayüzü değiştirme.", 'yüksek', 'refactor'),
}

SAST_AVOID = ("İşlevselliği koru. Girdi gerçekten sabit ve güvenliyse (kullanıcı verisi içermiyorsa) bulgu yanlış pozitiftir: "
              "gerekçeyi yorumla ve atla.")
DEFAULT = Guidance("Bulgudaki öneriyi uygula.", "Kapsam dışına çıkma; davranışı değiştirme.", 'orta', 'refactor')


def wave_of(rule: str, category: str) -> int:
    return RULE_WAVE.get(rule, CATEGORY_WAVE.get(category, DEFAULT_WAVE))


def label_of(rule: str, fallback: str) -> str:
    return catalog.RULE_LABELS.get(rule, fallback)


def guidance_for(rule: str, advice: Optional[str] = None) -> Guidance:
    """Kural başına talimat. SAST kuralları kendi `advice` metnini kullanır."""
    found = GUIDANCE.get(rule)
    if found is not None:
        return found
    if advice:
        return Guidance(advice, SAST_AVOID, 'orta', 'fix')
    return DEFAULT
