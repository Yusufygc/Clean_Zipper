import logging
import os
import pathspec
from typing import Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

GITIGNORE_NAME = '.gitignore'
GIT_INFO_EXCLUDE = os.path.join('.git', 'info', 'exclude')


def make_pathspec(lines) -> pathspec.PathSpec:
    """gitignore sözdizimiyle desen kümesi. Yeni pathspec'te 'gitignore', eskisinde 'gitwildmatch' fabrikası."""
    lines = list(lines)
    try:
        return pathspec.PathSpec.from_lines('gitignore', lines)
    except LookupError:
        return pathspec.PathSpec.from_lines('gitwildmatch', lines)


class GitignoreMatcher:
    """Git ile aynı öncelik kurallarıyla iç içe `.gitignore` değerlendirmesi.

    - Her klasördeki `.gitignore` tembel yüklenir (kökte ayrıca `.git/info/exclude`, daha düşük öncelikle).
    - Bir yol, kökten kendisine kadar her atanın `.gitignore`'una o atanın klasörüne göre göreli sorulur;
      eşleşen son kural kazanır (derindeki `.gitignore` öncelikli, `!` geri alabilir).
    - Ignore edilen bir klasörün içi geri eklenemez (git gibi).
    - Okunamayan `.gitignore` `load_errors` listesine yazılır; çağıran güvenlik açısından karar verir.
    - `tracked` verilirse (git'in izlediği, köke göre `/` ayraçlı yollar) git gibi davranılır: izlenen dosya
      kurala uysa bile ignore sayılmaz (kendi adını içeren `.gitignore`, `git add -f` ile eklenenler).
    """

    def __init__(self, root_path: str, tracked: Optional[Iterable[str]] = None):
        self.root = os.path.abspath(str(root_path))
        self.load_errors: List[str] = []
        self._specs: Dict[str, Optional[pathspec.PathSpec]] = {}
        self._dir_ignored: Dict[str, bool] = {}
        self._tracked: Set[str] = set()
        self._tracked_dirs: Set[str] = set()
        self.set_tracked(tracked)

    def set_tracked(self, tracked: Optional[Iterable[str]]):
        """İzlenen dosya kümesini (yeniden) ayarlar; None/boş: izleme bilgisi yok."""
        self._tracked = set(tracked or ())
        self._tracked_dirs = set()
        for rel in self._tracked:
            parts = rel.split('/')[:-1]
            for end in range(1, len(parts) + 1):
                self._tracked_dirs.add('/'.join(parts[:end]))
        self._dir_ignored.clear()

    def _relative_posix(self, path: str) -> str:
        return os.path.relpath(path, self.root).replace(os.sep, '/')

    # ------------------------------------------------------------------ #

    def is_ignored(self, path, is_dir: bool = False) -> bool:
        path = os.path.abspath(str(path))
        if not self._inside_root(path):
            return False
        if is_dir:
            return self.is_dir_ignored(path)
        if self._tracked and self._relative_posix(path) in self._tracked:
            return False
        if self.is_dir_ignored(os.path.dirname(path)):
            return True
        return self._evaluate(path, is_dir=False)

    def is_dir_ignored(self, dir_path) -> bool:
        dir_path = os.path.abspath(str(dir_path))
        if dir_path == self.root or not self._inside_root(dir_path):
            return False
        if self._tracked_dirs and self._relative_posix(dir_path) in self._tracked_dirs:
            return False                     # içinde izlenen dosya var: klasör budanmaz, dosyalar tek tek değerlendirilir
        key = os.path.normcase(dir_path)
        cached = self._dir_ignored.get(key)
        if cached is None:
            cached = self.is_dir_ignored(os.path.dirname(dir_path)) or self._evaluate(dir_path, is_dir=True)
            self._dir_ignored[key] = cached
        return cached

    def root_spec(self) -> Optional[pathspec.PathSpec]:
        return self._spec_for_dir(self.root)

    # ------------------------------------------------------------------ #

    def _inside_root(self, path: str) -> bool:
        relative = os.path.relpath(path, self.root)
        return relative != os.pardir and not relative.startswith(os.pardir + os.sep)

    def _evaluate(self, path: str, is_dir: bool) -> bool:
        parts = os.path.relpath(path, self.root).split(os.sep)
        ignored = False
        for depth in range(len(parts)):
            ancestor = os.path.join(self.root, *parts[:depth]) if depth else self.root
            spec = self._spec_for_dir(ancestor)
            if spec is None:
                continue
            relative = '/'.join(parts[depth:]) + ('/' if is_dir else '')
            decision = spec.check_file(relative).include
            if decision is not None:
                ignored = decision
        return ignored

    def _spec_for_dir(self, directory: str) -> Optional[pathspec.PathSpec]:
        key = os.path.normcase(directory)
        if key not in self._specs:
            lines: List[str] = []
            if directory == self.root:
                lines += self._read_lines(os.path.join(directory, GIT_INFO_EXCLUDE)) or []
            lines += self._read_lines(os.path.join(directory, GITIGNORE_NAME)) or []
            self._specs[key] = make_pathspec(lines) if lines else None
        return self._specs[key]

    def _read_lines(self, file_path: str) -> Optional[List[str]]:
        if not os.path.exists(file_path):
            return None
        try:
            # utf-8-sig: BOM'lu dosyalar; errors='replace': cp1254 gibi eski kodlamalar okumayı bozmaz
            with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                return f.read().splitlines()
        except OSError as e:
            message = f"{os.path.basename(file_path)} okunamadı: {e}"
            self.load_errors.append(message)
            logger.error("%s (%s)", message, file_path)
            return None


class GitignoreParser(GitignoreMatcher):
    """Eski API: kök `.gitignore`'u hemen yükler (`load_error` erken görünür); iç içe dosyaları da uygular."""

    def __init__(self, root_path: str, tracked: Optional[Iterable[str]] = None):
        super().__init__(root_path, tracked)
        self.root_path = str(root_path)
        self.root_spec()

    @property
    def spec(self) -> Optional[pathspec.PathSpec]:
        return self.root_spec()

    @property
    def load_error(self) -> Optional[str]:
        return self.load_errors[0] if self.load_errors else None

    @load_error.setter
    def load_error(self, value: Optional[str]):
        self.load_errors = [value] if value else []

    def should_ignore(self, file_path: str) -> bool:
        return self.is_ignored(file_path)
