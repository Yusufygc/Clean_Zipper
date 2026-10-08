"""Analizör kayıt defteri: yeni analizör eklemek yalnızca yeni bir dosya yazmayı gerektirir."""
import importlib
import pkgutil
from typing import Dict, Iterable, List, Type

from src.core.interfaces import IAnalyzer


class AnalyzerRegistry:
    def __init__(self):
        self._classes: Dict[str, Type[IAnalyzer]] = {}

    def register(self, cls: Type[IAnalyzer]) -> Type[IAnalyzer]:
        """Sınıf dekoratörü. Anahtar sınıf adıdır; aynı ada farklı sınıf kaydı hata verir."""
        existing = self._classes.get(cls.__name__)
        if existing is not None and existing is not cls:
            raise ValueError(f"'{cls.__name__}' adıyla başka bir analizör zaten kayıtlı.")
        self._classes[cls.__name__] = cls
        return cls

    def ids(self) -> List[str]:
        return sorted(self._classes)

    def create_all(self, disabled: Iterable[str] = ()) -> List[IAnalyzer]:
        skip = set(disabled)
        return [cls() for name, cls in sorted(self._classes.items()) if name not in skip]


default_registry = AnalyzerRegistry()
register_analyzer = default_registry.register


def load_builtin_analyzers(registry: AnalyzerRegistry = default_registry) -> AnalyzerRegistry:
    """src.analyzers altındaki tüm modülleri içe aktarır; dekoratörler kendilerini kaydeder."""
    package = importlib.import_module('src.analyzers')
    for module in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f'{package.__name__}.{module.name}')
    return registry
