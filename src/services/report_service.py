import html
import logging
from pathlib import Path
from src.core.interfaces import IReporter
from src.models.analysis_models import ProjectAnalysis, Severity
from src.services.audit_catalog import CATEGORY_NAMES

logger = logging.getLogger(__name__)


def _esc(value) -> str:
    """Raporlara giren her dış kaynaklı metin (dosya adı, yol, bulgu metni) buradan geçer."""
    return html.escape(str(value), quote=True)

REPORT_CSS = """<style>
        body {
            font-family: 'Segoe UI', Inter, Helvetica, sans-serif;
            background-color: #F8FAFC;
            color: #1E293B;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        .container { max-width: 1000px; margin: 40px auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            color: #FFFFFF; padding: 30px; border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 30px;
        }
        header h1 { margin: 0; font-size: 28px; font-weight: 800; }
        header p { margin: 10px 0 0 0; color: #94A3B8; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card-title { font-size: 12px; text-transform: uppercase; color: #64748B; font-weight: 700; margin-bottom: 5px; }
        .card-value { font-size: 24px; font-weight: 800; color: #0F172A; }
        .score-circle {
            display: inline-block; width: 100px; height: 100px; line-height: 100px;
            border-radius: 50%; text-align: center; font-size: 32px; font-weight: 900;
            color: #FFFFFF; margin-right: 20px; vertical-align: middle; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        .score-section {
            display: flex; align-items: center; background: #FFFFFF;
            border: 1px solid #E2E8F0; border-radius: 12px; padding: 25px; margin-bottom: 30px;
        }
        .score-details h2 { margin: 0; font-size: 22px; color: #0F172A; }
        .score-details p { margin: 5px 0 0 0; color: #64748B; }
        h3.section-title {
            font-size: 18px; font-weight: 800; color: #0F172A;
            border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; margin-top: 40px; margin-bottom: 20px;
        }
        .issue-card {
            background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
            padding: 18px; margin-bottom: 15px; position: relative; border-left: 5px solid #E2E8F0;
        }
        .issue-card.severity-critical { border-left-color: #DC2626; background-color: #FEF2F2; }
        .issue-card.severity-high { border-left-color: #EA580C; background-color: #FFF7ED; }
        .issue-card.severity-medium { border-left-color: #D97706; }
        .issue-card.severity-low { border-left-color: #2563EB; }
        .issue-card.severity-info { border-left-color: #16A34A; }
        .issue-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .issue-title { font-weight: 700; font-size: 15px; color: #0F172A; }
        .issue-desc { font-size: 13.5px; color: #475569; margin-bottom: 10px; }
        .issue-rec {
            font-size: 12.5px; color: #1E293B; background: rgba(255, 255, 255, 0.7);
            padding: 8px 12px; border-radius: 4px; border: 1px dashed #CBD5E1;
        }
        .badge { font-size: 10px; font-weight: 800; padding: 4px 8px; border-radius: 4px; color: #FFFFFF; }
        .badge-critical { background-color: #DC2626; }
        .badge-high { background-color: #EA580C; }
        .badge-medium { background-color: #D97706; }
        .badge-low { background-color: #2563EB; }
        .badge-info { background-color: #16A34A; }
        .path {
            font-family: monospace; font-size: 11px; color: #64748B;
            background: #F1F5F9; padding: 2px 6px; border-radius: 4px;
        }
        @media print {
            body { background-color: #FFFFFF; }
            .container { margin: 0; max-width: 100%; }
            .issue-card { page-break-inside: avoid; }
        }
    </style>"""


class ReportService(IReporter):
    """Proje analiz sonuçlarını ve kritik sorunları kurumsal HTML raporu olarak dışa aktaran servis."""

    SEVERITY_BADGES = {
        Severity.CRITICAL: '<span class="badge badge-critical">KRİTİK</span>',
        Severity.HIGH: '<span class="badge badge-high">YÜKSEK</span>',
        Severity.MEDIUM: '<span class="badge badge-medium">ORTA</span>',
        Severity.LOW: '<span class="badge badge-low">DÜŞÜK</span>',
        Severity.INFO: '<span class="badge badge-info">BİLGİ</span>'
    }

    def generate_report(self, analysis: ProjectAnalysis) -> str:
        """Ana HTML raporunu oluşturur."""
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
    <title>GitClean Proje Sağlık Raporu - {_esc(analysis.project_path.name)}</title>
    {self._get_css()}
</head>
<body>
    <div class="container">
        {self._build_header(analysis)}
        {self._build_score_section(analysis)}
        {self._build_stats_grid(analysis)}
        {self._build_category_section(analysis)}
        {self._build_critical_issues_section(analysis)}
        {self._build_other_issues_section(analysis)}
    </div>
</body>
</html>
"""

    def export_report(self, analysis: ProjectAnalysis, output_path: Path) -> bool:
        """Raporu belirtilen yola HTML dosyası olarak kaydeder."""
        try:
            content = self.generate_report(analysis)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            logger.exception("Rapor dışa aktarılamadı: %s", output_path)
            return False

    def _get_css(self) -> str:
        """HTML raporu için CSS stillerini döndürür."""
        return REPORT_CSS

    def _build_header(self, analysis: ProjectAnalysis) -> str:
        """Rapor başlık bölümünü oluşturur."""
        date_str = analysis.analysis_time.strftime('%d.%m.%Y - %H:%M:%S')
        return f"""<header>
            <h1>Proje Sağlık ve Uyumluluk Analizi</h1>
            <p>Proje Dizi Konumu: {_esc(analysis.project_path)}</p>
            <p>Raporlama Tarihi: {date_str}</p>
        </header>"""

    def _get_score_color(self, score: float) -> str:
        """Sağlık skoruna göre uygun renk kodunu döndürür."""
        if score >= 95: return "#00C853"
        if score >= 85: return "#2E7D32"
        if score >= 75: return "#558B2F"
        if score >= 65: return "#F9A825"
        if score >= 55: return "#EF6C00"
        if score >= 45: return "#E64A19"
        if score >= 35: return "#C62828"
        return "#B71C1C"

    def _build_score_section(self, analysis: ProjectAnalysis) -> str:
        """Sağlık skoru dairesini ve detaylarını oluşturur."""
        score_color = self._get_score_color(analysis.health_score)
        return f"""<div class="score-section">
            <div class="score-circle" style="background-color: {score_color};">{analysis.health_score:.0f}</div>
            <div class="score-details">
                <h2>Sağlık Notu: {_esc(analysis.health_status.value)}</h2>
                <p>Projenizin kurumsal standartlara, kod kalitesine ve temizlik kurallarına uyumluluk derecesidir.</p>
            </div>
        </div>"""

    def _build_stats_grid(self, analysis: ProjectAnalysis) -> str:
        """İstatistik ızgarasını (grid) oluşturur."""
        critical_count = len([i for i in analysis.issues if i.severity in [Severity.CRITICAL, Severity.HIGH]])
        return f"""<div class="grid">
            <div class="card">
                <div class="card-title">Toplam Dosya</div>
                <div class="card-value">{analysis.total_files}</div>
            </div>
            <div class="card">
                <div class="card-title">Proje Boyutu</div>
                <div class="card-value">{analysis.total_size_mb:.1f} MB</div>
            </div>
            <div class="card">
                <div class="card-title">Toplam Klasör</div>
                <div class="card-value">{analysis.total_dirs}</div>
            </div>
            <div class="card">
                <div class="card-title">Kritik ve Yüksek Sorunlar</div>
                <div class="card-value" style="color: #DC2626;">{critical_count}</div>
            </div>
        </div>"""

    def _build_category_section(self, analysis: ProjectAnalysis) -> str:
        """Kategori puanlarını (güvenlik, mimari, test, hijyen ...) en düşükten başlayarak kartlar olarak gösterir."""
        if not analysis.category_scores:
            return ''
        cards = ''.join(
            f"""<div class="card">
                <div class="card-title">{_esc(CATEGORY_NAMES.get(category, category))}</div>
                <div class="card-value" style="color: {self._get_score_color(score)};">{score:.0f}</div>
            </div>"""
            for category, score in sorted(analysis.category_scores.items(), key=lambda item: item[1]))
        return f'<h3 class="section-title">📊 KATEGORİ PUANLARI</h3>\n<div class="grid">{cards}</div>'

    def _build_issue_card(self, issue) -> str:
        """Tek bir sorunun HTML kartını oluşturur."""
        sev = getattr(issue, 'severity', Severity.INFO)
        badge = self.SEVERITY_BADGES.get(sev, '')
        file_info = f'<span class="path">{_esc(issue.file_path.name)}</span>' if getattr(issue, 'file_path', None) else ''
        rec_info = f'<div class="issue-rec"><b>💡 Öneri:</b> {_esc(issue.recommendation)}</div>' if getattr(issue, 'recommendation', None) else ''
        
        return f"""
        <div class="issue-card severity-{sev.name.lower()}">
            <div class="issue-header">
                <span class="issue-title">{_esc(issue.title)} {file_info}</span>
                {badge}
            </div>
            <div class="issue-desc">{_esc(issue.description)}</div>
            {rec_info}
        </div>
        """

    def _build_critical_issues_section(self, analysis: ProjectAnalysis) -> str:
        """Kritik ve yüksek öncelikli sorunlar bölümünü oluşturur."""
        critical_issues = [i for i in analysis.issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]
        
        html = '<h3 class="section-title">🚨 KRİTİK VE YÜKSEK ÖNCELİKLİ SORUNLAR</h3>\n'
        if not critical_issues:
            return html + """<div class="issue-card severity-info" style="border-left-width: 5px; text-align: center; padding: 30px;">
                <p style="font-weight: bold; color: #16A34A; font-size: 15px; margin: 0;">🎉 Harika! Projenizde hiçbir kritik veya yüksek öncelikli tasarım/güvenlik sorunu bulunamadı.</p>
            </div>"""
            
        for issue in critical_issues:
            html += self._build_issue_card(issue)
        return html

    def _build_other_issues_section(self, analysis: ProjectAnalysis) -> str:
        """Diğer (Orta, Düşük, Bilgi) bulgular bölümünü oluşturur."""
        other_issues = [i for i in analysis.issues if i.severity not in [Severity.CRITICAL, Severity.HIGH]]
        other_issues += analysis.warnings + analysis.suggestions
        
        html = '<h3 class="section-title">🔍 DİĞER BULGULAR VE İYİLEŞTİRMELER</h3>\n'
        if not other_issues:
            return html + '<p style="color: #64748B; font-size: 13px;">İyileştirme önerisi bulunmamaktadır.</p>'
            
        for issue in other_issues:
            html += self._build_issue_card(issue)
        return html