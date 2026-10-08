from typing import List, Tuple, Dict
from src.models.analysis_models import ProjectAnalysis

class RecommendationEngine:
    def generate_recommendations(self, analysis: ProjectAnalysis) -> List[Tuple[str, str, int]]:
        recs = []
        if analysis.total_size_mb > 100:
            recs.append(("Buyuk proje boyutu", f"Proje {analysis.total_size_mb:.1f} MB, buyuk dosyalari kontrol edin.", 80))
        if analysis.empty_dirs:
            recs.append(("Bos klasorler", f"{len(analysis.empty_dirs)} bos klasor bulundu, temizleyin.", 40))
        if analysis.duplicate_files:
            recs.append(("Cift dosyalar", f"{len(analysis.duplicate_files)} grup cift dosya, temizleyerek alan kazanin.", 75))
        if len(analysis.issues) > 5:
            recs.append(("Cok sayida sorun", f"{len(analysis.issues)} sorun tespit edildi, oncelikle kritik olanlari cozun.", 90))
        return self.prioritize_recommendations(recs)
    
    def prioritize_recommendations(self, recs):
        return sorted(recs, key=lambda x: x[2], reverse=True)
    
    def get_top_recommendations(self, analysis, count=5):
        return self.generate_recommendations(analysis)[:count]
