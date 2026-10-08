"""Git'ten salt-okunur bilgi. `git` yoksa, depo değilse ya da hata olursa `None` döner; asla fırlatmaz."""
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 15
CREATE_NO_WINDOW = 0x08000000      # Windows: konsolsuz uygulamada git için konsol penceresi açılmasın


def tracked_paths(root, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[Set[str]]:
    """`root` altında git'in izlediği dosyalar (`root`a göre, `/` ayraçlı). Bilinmiyorsa None.

    Güvenli kullanım: indeks kilidi alınmaz (GIT_OPTIONAL_LOCKS=0), fsmonitor kapalı, etkileşimli soru yok.
    """
    git = shutil.which('git')
    if git is None:
        logger.info("git bulunamadı; izlenen dosya bilgisi yok")
        return None
    environment = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
    try:
        completed = subprocess.run(
            [git, '-c', 'core.fsmonitor=false', '-C', str(Path(root)), 'ls-files', '-z'],
            capture_output=True, timeout=timeout, env=environment,
            creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("git ls-files çalıştırılamadı (%s): %s", root, e)
        return None
    if completed.returncode != 0:
        logger.info("git deposu değil ya da erişilemiyor (%s): %s", root,
                    completed.stderr.decode('utf-8', 'replace').strip()[:200])
        return None
    return {chunk.decode('utf-8', 'replace') for chunk in completed.stdout.split(b'\0') if chunk}
