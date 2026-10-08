import ast
import re
from typing import List

from src.languages.base import ClassInfo, FunctionInfo, LanguageSupport, SourceMetrics

_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)

# Sözdizimi hatalı dosyalarda içe aktarmaları yine de yakalamak için yedek.
_IMPORT_LINE = re.compile(r'^\s*import\s+([a-zA-Z0-9_.,\s]+)')
_FROM_LINE = re.compile(r'^\s*from\s+([a-zA-Z0-9_.]+)\s+import')


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """AST düğümlerini gezerek metodun siklomatik karmaşıklığını hesaplar."""
    def __init__(self):
        self.complexity = 1

    def _count(self, node):
        self.complexity += 1
        self.generic_visit(node)

    visit_If = visit_For = visit_AsyncFor = visit_While = visit_ExceptHandler = _count

    def visit_BoolOp(self, node):
        # Her 'and' veya 'or' ifadesi yeni bir karar noktası (dallanma) yaratır
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


class PythonLanguage(LanguageSupport):
    id = 'python'
    display_name = 'Python'
    extensions = ('.py',)
    approximate = False

    def analyze(self, text: str) -> SourceMetrics:
        lines = text.splitlines()
        blank = sum(1 for line in lines if not line.strip())
        comment = sum(1 for line in lines if line.strip().startswith('#'))
        metrics = SourceMetrics(
            language=self.id, total_lines=len(lines),
            code_lines=len(lines) - blank - comment, comment_lines=comment, blank_lines=blank,
        )
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            metrics.parse_ok = False
            metrics.imports = self._imports_from_lines(lines)
            return metrics

        for node in ast.walk(tree):
            if isinstance(node, _FUNCTION_NODES):
                visitor = CyclomaticComplexityVisitor()
                visitor.visit(node)
                metrics.functions.append(
                    FunctionInfo(node.name, node.lineno, node.end_lineno or node.lineno, visitor.complexity))
            elif isinstance(node, ast.ClassDef):
                methods = sum(1 for item in node.body if isinstance(item, _FUNCTION_NODES))
                metrics.classes.append(
                    ClassInfo(node.name, node.lineno, node.end_lineno or node.lineno, methods))
            elif isinstance(node, ast.Import):
                metrics.imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                metrics.imports.append(node.module)
        return metrics

    @staticmethod
    def _imports_from_lines(lines: List[str]) -> List[str]:
        found = []
        for line in lines:
            match = _IMPORT_LINE.match(line)
            if match:
                found.extend(part.strip().split(' ')[0] for part in match.group(1).split(',') if part.strip())
                continue
            match = _FROM_LINE.match(line)
            if match:
                found.append(match.group(1))
        return found
