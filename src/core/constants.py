"""Projeler arası ortak sabitler."""

# Analiz ve temizlik sırasında asla içine girilmeyen klasörler.
EXCLUDED_DIRS = frozenset({
    '.git', '__pycache__', '.venv', 'venv', 'env', 'ENV',
    'node_modules', '.idea', '.vs', 'dist', 'build',
    # Çerçeve derleme çıktıları ve araç önbellekleri (kaynak değil, üretilmiş içerik)
    '.next', '.nuxt', '.svelte-kit', '.turbo', '.parcel-cache', '.gradle',
    '.tox', '.mypy_cache', '.pytest_cache', '.ruff_cache', 'coverage', 'htmlcov',
})

# Yalnızca yanındaki dosyalar derleme sistemini gösteriyorsa dışlanan klasörler (aksi halde kaynak olabilir).
CONDITIONAL_EXCLUDED_DIRS = {
    'target': ('Cargo.toml', 'pom.xml', 'build.gradle', 'build.gradle.kts'),
    'bin': ('*.csproj', '*.fsproj', '*.vbproj'),
    'obj': ('*.csproj', '*.fsproj', '*.vbproj'),
}

# İçinde bu dosya olan klasör, adı ne olursa olsun Python sanal ortamıdır (ör. `myenv`).
VIRTUALENV_MARKER = 'pyvenv.cfg'
