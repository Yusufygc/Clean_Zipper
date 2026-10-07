import ast
from pathlib import Path
from typing import List, Tuple
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """AST düğümlerini gezerek metodun siklomatik karmaşıklığını hesaplar."""
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Her 'and' veya 'or' ifadesi yeni bir karar noktası (dallanma) yaratır
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


class CodeComplexityAnalyzer(BaseAnalyzer):
    """God Object, Bloated File ve Siklomatik Karmaşıklık analizlerini yapan kurumsal motor."""

    def __init__(self, priority: int = 12):
        super().__init__(priority)
        # Kurumsal temiz kod limitleri (Clean Code Guidelines)
        self.bloated_file_threshold = 400       # Dosya satır limiti (LOC)
        self.god_class_method_limit = 12        # Sınıf içi metot limiti
        self.god_class_loc_limit = 250          # Sınıf satır limiti
        self.complexity_limit = 10              # Metot karmaşıklık limiti

    @property
    def name(self) -> str:
        return "Kod Karmaşıklığı ve Tasarım Analizörü"

    @property
    def category(self) -> str:
        return "complexity"

    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []

        for root_path, _, filenames in self._walk_project(project_path):
            for filename in filenames:
                file_path = Path(root_path) / filename
                
                # Sadece Python kod dosyalarını analiz et
                if file_path.suffix.lower() != '.py':
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # 1. Aşırı Şişmiş Dosya (Bloated File) Kontrolü
                    loc = len(content.splitlines())
                    if loc > self.bloated_file_threshold:
                        results.append(self._create_result(
                            title=f"Aşırı Şişmiş Dosya: {file_path.name}",
                            description=f"Dosya toplamda {loc} satır kod içeriyor (Limit: {self.bloated_file_threshold}).",
                            severity=Severity.HIGH,
                            file_path=file_path,
                            recommendation="Bu dosyayı mantıksal olarak daha küçük, tek sorumluluğa (SRP) sahip modüllere veya alt sınıflara parçalayın."
                        ))

                    # AST yapısını çıkar
                    tree = ast.parse(content)

                    # 2. Sınıf Bazlı Analizler (God Class / God Object)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_loc = 0
                            if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                                class_loc = node.end_lineno - node.lineno + 1

                            methods = [item for item in node.body if isinstance(item, ast.FunctionDef)]
                            num_methods = len(methods)

                            # Limit aşımı durumunda 'God Object' uyarısı fırlat
                            if num_methods > self.god_class_method_limit or class_loc > self.god_class_loc_limit:
                                results.append(self._create_result(
                                    title=f"Tanrı Sınıf (God Object) Riski: {node.name}",
                                    description=f"'{node.name}' sınıfı {num_methods} metoda ve yaklaşık {class_loc} satır koda sahip. Bu sınıf sistemde çok fazla sorumluluk üstleniyor.",
                                    severity=Severity.HIGH,
                                    file_path=file_path,
                                    recommendation="Sınıfı SOLID prensiplerine uygun olarak parçalayın. Sınıfın sadece tek bir aktöre veya amaca hizmet etmesini sağlayın."
                                ))

                        # 3. Metot/Fonksiyon Bazlı Karmaşıklık Analizi (McCabe)
                        elif isinstance(node, ast.FunctionDef):
                            visitor = CyclomaticComplexityVisitor()
                            visitor.visit(node)
                            
                            if visitor.complexity > self.complexity_limit:
                                # Metodun hangi sınıfa ait olduğunu bulalım (İsteğe bağlı görsel iyileştirme)
                                results.append(self._create_result(
                                    title=f"Yüksek Karmaşıklık Saptandı: {node.name}()",
                                    description=f"Metodun siklomatik karmaşıklık skoru {visitor.complexity} olarak hesaplandı (Önerilen Sınır: {self.complexity_limit}). Çok fazla dallanma (if, loop) var.",
                                    severity=Severity.MEDIUM,
                                    file_path=file_path,
                                    recommendation="Metodu alt metotlara bölün (Extract Method). İç içe if-else bloklarını 'Guard Clauses' yöntemiyle düzleştirin."
                                ))

                except SyntaxError:
                    # Derlenemeyen veya geçici/bozuk Python dosyalarını güvenle atla
                    continue
                except Exception:
                    continue

        return results