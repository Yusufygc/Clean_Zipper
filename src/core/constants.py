"""Projeler arası ortak sabitler."""

# Analiz ve temizlik sırasında asla içine girilmeyen klasörler.
EXCLUDED_DIRS = frozenset({
    '.git', '__pycache__', '.venv', 'venv', 'env', 'ENV',
    'node_modules', '.idea', '.vs', 'dist', 'build',
})
