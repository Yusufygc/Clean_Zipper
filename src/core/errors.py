"""Uygulamaya özgü istisna sınıfları."""


class GitCleanError(Exception):
    """Uygulamanın bilerek fırlattığı tüm hataların tabanı."""


class ProjectNotSelectedError(GitCleanError, ValueError):
    """Proje seçilmeden analiz/arşiv/yedek istendi. ValueError tabanı mevcut yakalayıcıları bozmaz."""

    def __init__(self, message: str = "Önce bir proje seçin."):
        super().__init__(message)


class OperationBusyError(GitCleanError):
    """Projeyi değiştiren bir işlem (temizlik, arşiv, kopya, yedek) sürerken ikincisi istendi."""

    def __init__(self, running: str):
        super().__init__(f"Başka bir işlem sürüyor ({running}). Bitince tekrar deneyin.")
