"""Proje dosya sisteminin tek geçişte çıkarılan indeksi.

Analizörler kendi dizin taramasını yapmaz; bu indeks üzerinden çalışır.
Yalnızca standart kütüphane kullanır.
"""
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Optional, Tuple

from src.core.constants import EXCLUDED_DIRS
from src.core.exclusions import is_excluded_dir

BINARY_SNIFF_BYTES = 8192
PARTIAL_HASH_BYTES = 64 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_TEXT_BYTES = 2_000_000
TEXT_CACHE_CHAR_BUDGET = 64_000_000
PROGRESS_EVERY_FILES = 1000

# Sırayla denenir. cp1254 Türkçe Windows dosyaları içindir; latin-1 hiçbir zaman başarısız olmaz.
TEXT_ENCODINGS = ('utf-8-sig', 'cp1254', 'latin-1')


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
        self._memo: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def build(cls, root: Path, excluded: FrozenSet[str] = EXCLUDED_DIRS,
              progress: Optional[Callable[[int], None]] = None) -> 'ProjectIndex':
        root = Path(root).resolve()
        index = cls(root)
        stack: List[Tuple[Path, str, int]] = [(root, '', 0)]
        reported = 0
        while stack:
            directory, rel, depth = stack.pop()
            index.max_depth = max(index.max_depth, depth)
            index._scan_directory(directory, rel, depth, excluded, stack)
            if progress and len(index.files) - reported >= PROGRESS_EVERY_FILES:
                reported = len(index.files)
                progress(reported)
        return index

    def _scan_directory(self, directory: Path, rel: str, depth: int,
                        excluded: FrozenSet[str], stack: list):
        file_count = dir_count = 0
        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as e:
            self.errors.append((directory, str(e)))
            return
        sibling_names = [e.name for e in entries]

        for entry in entries:
            try:
                is_symlink = entry.is_symlink()
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError as e:
                self.errors.append((Path(entry.path), str(e)))
                continue

            if is_dir:
                dir_count += 1
                if not is_excluded_dir(entry.path, entry.name, sibling_names, excluded):
                    child_rel = f"{rel}/{entry.name}" if rel else entry.name
                    stack.append((Path(entry.path), child_rel, depth + 1))
                continue

            file_count += 1
            if is_symlink:
                continue
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as e:
                self.errors.append((Path(entry.path), str(e)))
                continue
            ext = os.path.splitext(entry.name)[1].lower()
            self.files.append(FileEntry(
                path=Path(entry.path),
                rel=f"{rel}/{entry.name}" if rel else entry.name,
                size=st.st_size, mtime=st.st_mtime, ext=ext,
            ))
            self.total_size += st.st_size
            self.ext_counts[ext] = self.ext_counts.get(ext, 0) + 1
            self.ext_sizes[ext] = self.ext_sizes.get(ext, 0) + st.st_size

        if depth > 0:
            self.dirs.append(DirEntry(directory, rel, depth, file_count, dir_count))

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

    def memo(self, namespace: str, entry: FileEntry, factory: Callable[[], Any]) -> Any:
        """Dosya başına türetilmiş veriyi (None dahil) bir kez üretir; analizörler arasında paylaşılır."""
        bucket = self._memo.setdefault(namespace, {})
        if entry.rel not in bucket:
            bucket[entry.rel] = factory()
        return bucket[entry.rel]

    # ------------------------------------------------------------------ #
    #  İçerik erişimi                                                    #
    # ------------------------------------------------------------------ #

    def is_binary(self, entry: FileEntry) -> bool:
        """İlk 8 KB içinde NUL baytı varsa ikilik sayılır. Okunamayan dosya da ikilik sayılır."""
        cached = self._binary.get(entry.rel)
        if cached is not None:
            return cached
        try:
            with open(entry.path, 'rb') as f:
                chunk = f.read(BINARY_SNIFF_BYTES)
        except OSError:
            chunk = b'\x00'
        result = b'\x00' in chunk
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
        binary = b'\x00' in data[:BINARY_SNIFF_BYTES]
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
