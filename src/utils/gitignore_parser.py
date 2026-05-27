import os
import pathspec
from typing import Optional

class GitignoreParser:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.spec: Optional[pathspec.PathSpec] = None
        self._load()
    
    def _load(self):
        gitignore_path = os.path.join(self.root_path, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.spec = pathspec.PathSpec.from_lines('gitwildmatch', content.splitlines())
    
    def should_ignore(self, file_path: str) -> bool:
        if not self.spec:
            return False
        relative_path = os.path.relpath(file_path, self.root_path).replace('\\', '/')
        return self.spec.match_file(relative_path)
