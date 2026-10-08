"""Projeler arası ortak sabitler."""

# Analiz ve temizlik sırasında asla içine girilmeyen klasörler.
EXCLUDED_DIRS = frozenset({
    '.git', '__pycache__', '.venv', 'venv', 'env', 'ENV',
    'node_modules', '.idea', '.vs', 'dist', 'build',
    # Çerçeve derleme çıktıları ve araç önbellekleri (kaynak değil, üretilmiş içerik)
    '.next', '.nuxt', '.svelte-kit', '.turbo', '.parcel-cache', '.gradle',
    '.tox', '.mypy_cache', '.pytest_cache', '.ruff_cache', 'coverage', 'htmlcov',
})
