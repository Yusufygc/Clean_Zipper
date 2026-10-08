import pytest

from src.core.base_analyzer import BaseAnalyzer
from src.core.registry import AnalyzerRegistry, default_registry, load_builtin_analyzers

EXPECTED_BUILTINS = {
    'ArchitectureAnalyzer', 'CloneAnalyzer', 'CodeComplexityAnalyzer', 'DeadCodeAnalyzer', 'DeadWeightAnalyzer', 'DuplicateFinder',
    'EmptyFolderFinder', 'LanguageStatsAnalyzer', 'MagicNumberAnalyzer', 'SecurityLeakAnalyzer', 'SizeAnalyzer',
    'StructureAnalyzer', 'TypeAnalyzer',
}


def make(name):
    return type(name, (BaseAnalyzer,), {'analyze': lambda self, index: []})


def test_register_and_create_all():
    registry = AnalyzerRegistry()
    a, b = make('A'), make('B')
    assert registry.register(a) is a       # dekoratör sınıfı olduğu gibi döner
    registry.register(b)
    assert registry.ids() == ['A', 'B']
    assert [type(x) for x in registry.create_all()] == [a, b]


def test_disabled_ids_are_skipped():
    registry = AnalyzerRegistry()
    registry.register(make('A'))
    registry.register(make('B'))
    assert [type(x).__name__ for x in registry.create_all(disabled=['A'])] == ['B']


def test_same_class_twice_is_idempotent_but_name_clash_fails():
    registry = AnalyzerRegistry()
    a = make('A')
    registry.register(a)
    registry.register(a)
    assert registry.ids() == ['A']
    with pytest.raises(ValueError):
        registry.register(make('A'))


def test_create_all_returns_fresh_instances():
    registry = AnalyzerRegistry()
    registry.register(make('A'))
    assert registry.create_all()[0] is not registry.create_all()[0]


def test_registries_are_isolated():
    one, two = AnalyzerRegistry(), AnalyzerRegistry()
    one.register(make('A'))
    assert two.ids() == []


def test_builtin_discovery_finds_all_nine_and_is_idempotent():
    load_builtin_analyzers()
    load_builtin_analyzers()
    assert set(default_registry.ids()) == EXPECTED_BUILTINS
    assert len(default_registry.create_all()) == 13
