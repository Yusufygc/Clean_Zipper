"""Git'ten salt-okunur bilgi. `git` yoksa, depo değilse ya da hata olursa `None` döner; asla fırlatmaz."""
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 15
HISTORY_TIMEOUT_SECONDS = 30       # geçmiş sorguları ls-files'tan yavaştır
CREATE_NO_WINDOW = 0x08000000      # Windows: konsolsuz uygulamada git için konsol penceresi açılmasın
_COMMIT_MARK = '\x01'              # `--pretty=format:%x01...` ile her commit satırı bu işaretle başlar


@dataclass(frozen=True)
class Commit:
    sha: str
    time: int                      # unix saniye
    files: Tuple[str, ...]         # değişen dosyalar (köke göre, '/' ayraçlı)


@dataclass(frozen=True)
class HistoryEntry:
    sha: str                       # yolun EKLENDİĞİ en son commit (kısa)
    time: int


def _run_git(root, args: Sequence[str], timeout: float) -> Optional[bytes]:
    """Salt-okunur git çağrısı; başarılıysa stdout baytları, aksi hâlde None.

    Güvenli kullanım: indeks kilidi alınmaz (GIT_OPTIONAL_LOCKS=0), fsmonitor kapalı, etkileşimli soru yok.
    """
    git = shutil.which('git')
    if git is None:
        logger.info("git bulunamadı; git bilgisi yok")
        return None
    environment = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
    try:
        completed = subprocess.run(
            [git, '-c', 'core.fsmonitor=false', '-c', 'core.quotepath=false', '-C', str(Path(root)), *args],
            capture_output=True, timeout=timeout, env=environment,
            creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("git %s çalıştırılamadı (%s): %s", args[0], root, e)
        return None
    if completed.returncode != 0:
        logger.info("git deposu değil ya da erişilemiyor (%s): %s", root,
                    completed.stderr.decode('utf-8', 'replace').strip()[:200])
        return None
    return completed.stdout


def tracked_paths(root, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[Set[str]]:
    """`root` altında git'in izlediği dosyalar (`root`a göre, `/` ayraçlı). Bilinmiyorsa None."""
    out = _run_git(root, ['ls-files', '-z'], timeout)
    if out is None:
        return None
    return {chunk.decode('utf-8', 'replace') for chunk in out.split(b'\0') if chunk}


def _parse_log(out: bytes) -> List[Commit]:
    """`--pretty=format:%x01%H %ct` + `--name-only` çıktısını commit listesine çevirir."""
    commits: List[Commit] = []
    sha, when, files = '', 0, []
    for line in out.decode('utf-8', 'replace').splitlines():
        if line.startswith(_COMMIT_MARK):
            if sha:
                commits.append(Commit(sha, when, tuple(files)))
            fields = line[1:].split()
            sha, when, files = fields[0], int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else 0, []
        elif line.strip() and sha:
            files.append(line.strip())
    if sha:
        commits.append(Commit(sha, when, tuple(files)))
    return commits


def recent_commits(root, limit: int = 500, timeout: float = HISTORY_TIMEOUT_SECONDS) -> Optional[List[Commit]]:
    """Geçerli dalın son `limit` commit'i (yeniden eskiye; merge commit'leri hariç) ve değişen dosyaları."""
    out = _run_git(root, ['log', '-n', str(limit), '--no-merges', '--relative', '--name-only',
                          '--pretty=format:%x01%H %ct'], timeout)
    return None if out is None else _parse_log(out)


def history_paths(root, pathspecs: Sequence[str], timeout: float = HISTORY_TIMEOUT_SECONDS) -> Optional[Dict[str, HistoryEntry]]:
    """Tüm dal/etiketlerde EKLENMİŞ olan ve `pathspecs` ile eşleşen yollar; yol -> eklendiği en son commit.

    Dosya sonradan silinmiş ya da izlemeden çıkarılmış olsa bile tarihçede durduğu için burada görünür.
    """
    out = _run_git(root, ['log', '--branches', '--tags', '--remotes', '--relative', '--diff-filter=A', '--name-only',
                          '--pretty=format:%x01%h %ct', '--', *pathspecs], timeout)
    if out is None:
        return None
    found: Dict[str, HistoryEntry] = {}
    for commit in _parse_log(out):                       # yeniden eskiye: ilk görülen en son ekleme
        for path in commit.files:
            found.setdefault(path, HistoryEntry(commit.sha, commit.time))
    return found
