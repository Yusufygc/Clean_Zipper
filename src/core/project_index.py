"""Proje dosya sisteminin tek geçişte çıkarılan indeksi.

Analizörler kendi dizin taramasını yapmaz; bu indeks üzerinden çalışır.
Yalnızca standart kütüphane kullanır.
"""
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

from src.core.constants import EXCLUDED_DIRS
from src.core.exclusions import is_excluded_dir
from src.utils.git_info import tracked_paths
from src.utils.gitignore_parser import GitignoreMatcher

BINARY_SNIFF_BYTES = 8192
PARTIAL_HASH_BYTES = 64 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_TEXT_BYTES = 2_000_000
TEXT_CACHE_CHAR_BUDGET = 64_000_000
PROGRESS_EVERY_FILES = 1000

# Sırayla denenir. cp1254 Türkçe Windows dosyaları içindir; latin-1 hiçbir zaman başarısız olmaz.
TEXT_ENCODINGS = ('utf-8-sig', 'cp1254', 'latin-1')
# BOM'lu UTF-16/32 metinde NUL baytı olağandır (ör. PowerShell `>` çıktısı, bazı Visual Studio dosyaları): ikilik sayılmaz.
# UTF-32 önce denenir: UTF-32 LE BOM'u UTF-16 LE BOM'uyla başlar.
UNICODE_BOMS = ((b'\xff\xfe\x00\x00', 'utf-32'), (b'\x00\x00\xfe\xff', 'utf-32'),
                (b'\xff\xfe', 'utf-16'), (b'\xfe\xff', 'utf-16'))


# BOM'suz UTF-16: NUL baytların en az bu kadarı tek (LE) ya da çift (BE) konumlarda, öbür konumlarda hiç NUL yok.
# `C:\2UYGULAMALAR` taramasında NUL içeren ~152 bin BOM'suz dosyanın 13'ünü yakaladı, hepsi gerçek UTF-16 metindi.
UTF16_NUL_RATIO = 0.9
_MIN_UTF16_SNIFF = 8


def _bom_encoding(data: bytes) -> Optional[str]:
    return next((encoding for bom, encoding in UNICODE_BOMS if data.startswith(bom)), None)


def _bomless_utf16(chunk: bytes) -> Optional[str]:
    """ASCII ağırlıklı BOM'suz UTF-16 metnin kodlaması ('utf-16-le' / 'utf-16-be'); değilse None."""
    if len(chunk) < _MIN_UTF16_SNIFF:
        return None
    even, odd = chunk[0::2], chunk[1::2]
    for encoding, zeros, others in (('utf-16-le', odd, even), ('utf-16-be', even, odd)):
        if b'\x00' not in others and zeros.count(0) >= UTF16_NUL_RATIO * len(zeros):
            try:
                chunk[:len(chunk) - len(chunk) % 2].decode(encoding)
            except UnicodeDecodeError:
                continue
            return encoding
    return None


def _unicode_encoding(data: bytes) -> Optional[str]:
    """NUL içerebilen Unicode metin kodlaması: önce BOM, sonra BOM'suz UTF-16 sezgisi (ilk 8 KB)."""
    return _bom_encoding(data) or _bomless_utf16(data[:BINARY_SNIFF_BYTES])


def looks_binary(chunk: bytes) -> bool:
    """NUL baytı içeren ve UTF-16/32 (BOM'lu ya da BOM'suz UTF-16) olmayan veri ikiliktir."""
    return b'\x00' in chunk and _unicode_encoding(chunk) is None


@dataclass(frozen=True)
class FileEntry:
    path: Path
    rel: str          # köke göre, '/' ayraçlı
    size: int
    mtime: float
    ext: str          # küçük harf, noktayla (ör. '.py'); uzantısız dosyada ''


@dataclass(frozen=True)
class DirEntry:
    path: Path
    rel: str
    depth: int        # kökün doğrudan çocuğu = 1
    file_count: int   # doğrudan çocuk dosyalar (symlink dahil)
    dir_count: int    # doğrudan çocuk klasörler (dışlananlar dahil)


class ProjectIndex:
    def __init__(self, root: Path):
        self.root = root
        self.files: List[FileEntry] = []
        self.dirs: List[DirEntry] = []
        self.errors: List[Tuple[Path, str]] = []
        self.total_size = 0
        self.max_depth = 0
        self.ext_counts: Dict[str, int] = {}
        self.ext_sizes: Dict[str, int] = {}
        self._binary: Dict[str, bool] = {}
        self._text_cache: Dict[str, str] = {}
        self._text_cache_chars = 0
        # rel -> neden ('too_large', 'unreadable', 'parse_error'): analize giremeyen dosyalar
        self.skipped: Dict[str, str] = {}
        # .gitignore ile dışarıda kalanlar. Budanan klasörün içindeki dosyalar sayılmaz (içine girilmez).
        self.gitignored: Dict[str, int] = {'files': 0, 'dirs': 0}
        self.gitignore_applied = False
        self._gitignore: Optional[GitignoreMatcher] = None
        self._git_tracked: Optional[Set[str]] = None
        self._git_tracked_loaded = False
        self._memo: Dict[str, Dict[str, Any]] = {}
        self._memo_cost: Dict[str, int] = {}

    @classmethod
    def build(cls, root: Path, excluded: FrozenSet[str] = EXCLUDED_DIRS,
              progress: Optional[Callable[[int], None]] = None,
              respect_gitignore: bool = True) -> 'ProjectIndex':
        root = Path(root).resolve()
        index = cls(root)
        if respect_gitignore:
            # İzlenen dosyalar kurala uysa bile ignore sayılmaz (git semantiği); aynı liste güvenlik analizörü için saklanır.
            index._git_tracked = tracked_paths(root)
            index._git_tracked_loaded = True
            index._gitignore = GitignoreMatcher(str(root), tracked=index._git_tracked)
            index.gitignore_applied = True
        stack: List[Tuple[Path, str, int]] = [(root, '', 0)]
        reported = 0
        while stack:
            directory, rel, depth = stack.pop()
            index.max_depth = max(index.max_depth, depth)
            index._scan_directory(directory, rel, depth, excluded, stack)
            if progress and len(index.files) - reported >= PROGRESS_EVERY_FILES:
                reported = len(index.files)
                progress(reported)
        if index._gitignore is not None:
            index.errors.extend((root, message) for message in index._gitignore.load_errors)
        return index

    def _scan_directory(self, directory: Path, rel: str, depth: int,
                        excluded: FrozenSet[str], stack: list):
        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as e:
            self.errors.append((directory, str(e)))
            return
        sibling_names = [e.name for e in entries]
        file_count = dir_count = 0

        for entry in entries:
            kind = self._entry_kind(entry)
            if kind == 'dir':
                dir_count += 1
                child = self._subdirectory(entry, rel, depth, excluded, sibling_names)
                if child is not None:
                    stack.append(child)
            elif kind is not None:
                file_count += 1
                if kind == 'file':
                    self._add_file(entry, rel)

        if depth > 0:
            self.dirs.append(DirEntry(directory, rel, depth, file_count, dir_count))

    def _entry_kind(self, entry: 'os.DirEntry') -> Optional[str]:
        """'dir' | 'symlink' | 'file'; okunamayan girdi hata listesine yazılır ve None döner."""
        try:
            is_symlink = entry.is_symlink()
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError as e:
            self.errors.append((Path(entry.path), str(e)))
            return None
        if is_dir:
            return 'dir'
        return 'symlink' if is_symlink else 'file'

    def _subdirectory(self, entry: 'os.DirEntry', rel: str, depth: int, excluded: FrozenSet[str],
                      sibling_names: List[str]) -> Optional[Tuple[Path, str, int]]:
        """Alt klasör dışlanmamış ve .gitignore'da değilse taranacaklar yığınına eklenecek (yol, rel, derinlik) girdisi."""
        if is_excluded_dir(entry.path, entry.name, sibling_names, excluded):
            return None
        if self._gitignore is not None and self._gitignore.is_ignored(entry.path, is_dir=True):
            self.gitignored['dirs'] += 1
            return None
        return Path(entry.path), (f"{rel}/{entry.name}" if rel else entry.name), depth + 1

    def _add_file(self, entry: 'os.DirEntry', rel: str):
        if self._gitignore is not None and self._gitignore.is_ignored(entry.path):
            self.gitignored['files'] += 1
            return
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError as e:
            self.errors.append((Path(entry.path), str(e)))
            return
        ext = os.path.splitext(entry.name)[1].lower()
        self.files.append(FileEntry(
            path=Path(entry.path),
            rel=f"{rel}/{entry.name}" if rel else entry.name,
            size=st.st_size, mtime=st.st_mtime, ext=ext,
        ))
        self.total_size += st.st_size
        self.ext_counts[ext] = self.ext_counts.get(ext, 0) + 1
        self.ext_sizes[ext] = self.ext_sizes.get(ext, 0) + st.st_size

    # ------------------------------------------------------------------ #
    #  Sorgular                                                          #
    # ------------------------------------------------------------------ #

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_dirs(self) -> int:
        return len(self.dirs)

    def files_with_ext(self, *exts: str) -> Iterator[FileEntry]:
        wanted = {e.lower() for e in exts}
        return (f for f in self.files if f.ext in wanted)

    @property
    def git_tracked(self) -> Optional[Set[str]]:
        """Git'in izlediği dosyalar (köke göre, '/' ayraçlı); git yoksa / depo değilse None. İlk erişimde bir kez çalışır."""
        if not self._git_tracked_loaded:
            self._git_tracked = tracked_paths(self.root)
            self._git_tracked_loaded = True
        return self._git_tracked

    def memo(self, namespace: str, entry: FileEntry, factory: Callable[[], Any],
             cost: Optional[Callable[[Any], int]] = None, budget: Optional[int] = None) -> Any:
        """Dosya başına türetilmiş veriyi (None dahil) bir kez üretir; analizörler arasında paylaşılır.

        `cost` ve `budget` verilirse ad alanının toplam maliyeti bütçeyi aşınca yeni değerler saklanmaz
        (yine hesaplanıp döner, yalnızca önbelleğe alınmaz): büyük metinler için bellek tavanı.
        """
        bucket = self._memo.setdefault(namespace, {})
        if entry.rel in bucket:
            return bucket[entry.rel]
        value = factory()
        if cost is None:
            bucket[entry.rel] = value
        else:
            used = self._memo_cost.get(namespace, 0)
            price = cost(value)
            if budget is None or used + price <= budget:
                bucket[entry.rel] = value
                self._memo_cost[namespace] = used + price
        return value

    # ------------------------------------------------------------------ #
    #  İçerik erişimi                                                    #
    # ------------------------------------------------------------------ #

    def is_binary(self, entry: FileEntry) -> bool:
        """İlk 8 KB içinde NUL baytı varsa ikilik sayılır (BOM'lu UTF-16/32 hariç). Okunamayan dosya da ikilik sayılır."""
        cached = self._binary.get(entry.rel)
        if cached is not None:
            return cached
        try:
            with open(entry.path, 'rb') as f:
                chunk = f.read(BINARY_SNIFF_BYTES)
        except OSError:
            chunk = b'\x00'
        result = looks_binary(chunk)
        self._binary[entry.rel] = result
        return result

    def mark_skipped(self, entry: FileEntry, reason: str):
        """Analize giremeyen dosyayı kaydeder (ilk neden korunur); sonuçta 'atlananlar' olarak raporlanır."""
        self.skipped.setdefault(entry.rel, reason)

    def read_text(self, entry: FileEntry, max_bytes: int = DEFAULT_MAX_TEXT_BYTES) -> Optional[str]:
        """Metin dosyasının içeriği. İkilik, çok büyük veya okunamayan dosyada None."""
        cached = self._text_cache.get(entry.rel)
        if cached is not None:
            return cached
        if entry.size > max_bytes:
            self.mark_skipped(entry, 'too_large')
            return None
        try:
            with open(entry.path, 'rb') as f:
                data = f.read(max_bytes + 1)
        except OSError:
            self.mark_skipped(entry, 'unreadable')
            return None
        if len(data) > max_bytes:
            self.mark_skipped(entry, 'too_large')
            return None
        binary = looks_binary(data[:BINARY_SNIFF_BYTES])
        self._binary[entry.rel] = binary
        if binary:
            return None

        text = self._decode(data)
        if self._text_cache_chars + len(text) <= TEXT_CACHE_CHAR_BUDGET:
            self._text_cache[entry.rel] = text
            self._text_cache_chars += len(text)
        return text

    @staticmethod
    def _decode(data: bytes) -> str:
        unicode = _unicode_encoding(data)
        if unicode is not None:
            return data.decode(unicode, errors='replace')  # BOM'u codec atar; tek kalan son bayt '�' olur
        for encoding in TEXT_ENCODINGS[:-1]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode(TEXT_ENCODINGS[-1])

    def hash_file(self, entry: FileEntry, partial: bool = False) -> str:
        """blake2b özeti. partial=True yalnızca ilk 64 KB'ı özetler. OSError çağırana gider."""
        digest = hashlib.blake2b()
        with open(entry.path, 'rb') as f:
            if partial:
                digest.update(f.read(PARTIAL_HASH_BYTES))
            else:
                while True:
                    chunk = f.read(HASH_CHUNK_BYTES)
                    if not chunk:
                        break
                    digest.update(chunk)
        return digest.hexdigest()
