"""QML'den gelen dosya yolu / URL dönüşümü."""
from PySide6.QtCore import QUrl


def local_path(text: str) -> str:
    """`file:///C:/a%20b` gibi QML dosya URL'sini yerel yola çevirir; düz yolu olduğu gibi döner.

    Dize kesme (`[8:]`) yerine `QUrl.toLocalFile`: yüzde kodlamasını (`%20`, `%C5%9F`) çözer, POSIX'te baştaki
    `/`'yi korur (`file:///home/x` -> `/home/x`) ve ağ yollarını (`file://sunucu/pay`) UNC yola çevirir.
    """
    if not text or not text.lower().startswith('file:'):
        return text or ''
    return QUrl(text).toLocalFile()
