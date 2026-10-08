import logging
import os
import pathspec
from typing import Optional

logger = logging.getLogger(__name__)


class GitignoreParser:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.spec: Optional[pathspec.PathSpec] = None
        # .gitignore var ama okunamadıysa dolu: arşivleme bu durumda gizli dosyaları sızdırabileceğinden reddedilir.
        self.load_error: Optional[str] = None
        self._load()

    def _load(self):
        gitignore_path = os.path.join(self.root_path, '.gitignore')
        if not os.path.exists(gitignore_path):
            return
        try:
            # utf-8-sig: BOM'lu dosyalar; errors='replace': cp1254 gibi eski kodlamalar okumayı bozmaz
            with open(gitignore_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                content = f.read()
        except OSError as e:
            self.load_error = f".gitignore okunamadı: {e}"
            logger.error("%s (%s)", self.load_error, gitignore_path)
            return
        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', content.splitlines())

    def should_ignore(self, file_path: str) -> bool:
        if not self.spec:
            return False
        relative_path = os.path.relpath(file_path, self.root_path).replace('\\', '/')
        return self.spec.match_file(relative_path)
