import os
from pathlib import Path
from typing import Dict, Optional, List

class CleanupService:
    CLEANUP_PATTERNS = {
        'python': {'extensions': ['.pyc', '.pyo'], 'directories': ['__pycache__']},
        'general': {'extensions': ['.log', '.tmp', '.bak'], 'directories': []}
    }
    
    def preview_cleanup(self, project_path: Path, categories: Optional[List[str]] = None) -> Dict:
        if not categories:
            categories = list(self.CLEANUP_PATTERNS.keys())
        preview = {'total_files': 0, 'total_size': 0, 'files': []}
        for category in categories:
            if category in self.CLEANUP_PATTERNS:
                patterns = self.CLEANUP_PATTERNS[category]
                for root, dirs, files in os.walk(project_path):
                    dirs[:] = [d for d in dirs if d != '.git']
                    for file in files:
                        fp = Path(root) / file
                        if fp.suffix.lower() in patterns['extensions']:
                            try:
                                size = fp.stat().st_size
                                preview['files'].append({'path': str(fp), 'size': size})
                                preview['total_files'] += 1
                                preview['total_size'] += size
                            except OSError:
                                pass
        return preview
    
    def cleanup(self, project_path: Path, dry_run: bool = True, **kwargs) -> Dict:
        preview = self.preview_cleanup(project_path)
        result = {'success': False, 'dry_run': dry_run, 'cleaned_files': 0, 'cleaned_size': 0}
        if dry_run:
            result['success'] = True
            return result
        for f in preview['files']:
            try:
                Path(f['path']).unlink()
                result['cleaned_files'] += 1
                result['cleaned_size'] += f['size']
            except OSError:
                pass
        result['success'] = True
        return result
