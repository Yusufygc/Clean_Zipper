import os
from pathlib import Path
from datetime import datetime
from src.core.interfaces import IReporter
from src.models.analysis_models import ProjectAnalysis, Severity, HealthStatus

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
        # Sağlık skoru renk kodunu belirleme (Widget renkleriyle uyumlu)
        score = analysis.health_score
        if score >= 95: score_color = "#00C853"
        elif score >= 85: score_color = "#2E7D32"
        elif score >= 75: score_color = "#558B2F"
        elif score >= 65: score_color = "#F9A825"
        elif score >= 55: score_color = "#EF6C00"
        elif score >= 45: score_color = "#E64A19"
        elif score >= 35: score_color = "#C62828"
        else: score_color = "#B71C1C"

        # Kritik ve Yüksek öncelikli sorunları filtreleme
        critical_issues = [i for i in analysis.issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]
        other_issues = [i for i in analysis.issues if i.severity not in [Severity.CRITICAL, Severity.HIGH]]
        other_issues += analysis.warnings + analysis.suggestions

        # HTML Şablonunu Oluşturma
        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>GitClean Proje Sağlık Raporu - {analysis.project_path.name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Inter, Helvetica, sans-serif;
            background-color: #F8FAFC;
            color: #1E293B;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 40px auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            color: #FFFFFF;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }}
        header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 800;
        }}
        header p {{
            margin: 10px 0 0 0;
            color: #94A3B8;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card-title {{
            font-size: 12px;
            text-transform: uppercase;
            color: #64748B;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        .card-value {{
            font-size: 24px;
            font-weight: 800;
            color: #0F172A;
        }}
        .score-circle {{
            display: inline-block;
            width: 100px;
            height: 100px;
            line-height: 100px;
            border-radius: 50%;
            text-align: center;
            font-size: 32px;
            font-weight: 900;
            color: #FFFFFF;
            background-color: {score_color};
            margin-right: 20px;
            vertical-align: middle;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        .score-section {{
            display: flex;
            align-items: center;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        .score-details h2 {{
            margin: 0;
            font-size: 22px;
            color: #0F172A;
        }}
        .score-details p {{
            margin: 5px 0 0 0;
            color: #64748B;
        }}
        h3.section-title {{
            font-size: 18px;
            font-weight: 800;
            color: #0F172A;
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 8px;
            margin-top: 40px;
            margin-bottom: 20px;
        }}
        .issue-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 15px;
            position: relative;
            border-left: 5px solid #E2E8F0;
        }}
        .issue-card.severity-critical {{ border-left-color: #DC2626; background-color: #FEF2F2; }}
        .issue-card.severity-high {{ border-left-color: #EA580C; background-color: #FFF7ED; }}
        .issue-card.severity-medium {{ border-left-color: #D97706; }}
        .issue-card.severity-low {{ border-left-color: #2563EB; }}
        .issue-card.severity-info {{ border-left-color: #16A34A; }}
        
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .issue-title {{
            font-weight: 700;
            font-size: 15px;
            color: #0F172A;
        }}
        .issue-desc {{
            font-size: 13.5px;
            color: #475569;
            margin-bottom: 10px;
        }}
        .issue-rec {{
            font-size: 12.5px;
            color: #1E293B;
            background: rgba(255, 255, 255, 0.7);
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px dashed #CBD5E1;
        }}
        .badge {{
            font-size: 10px;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
            color: #FFFFFF;
        }}
        .badge-critical {{ background-color: #DC2626; }}
        .badge-high {{ background-color: #EA580C; }}
        .badge-medium {{ background-color: #D97706; }}
        .badge-low {{ background-color: #2563EB; }}
        .badge-info {{ background-color: #16A34A; }}
        
        .path {{
            font-family: monospace;
            font-size: 11px;
            color: #64748B;
            background: #F1F5F9;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        
        @media print {{
            body {{ background-color: #FFFFFF; }}
            .container {{ margin: 0; max-width: 100%; }}
            .issue-card {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Proje Sağlık ve Uyumluluk Analizi</h1>
            <p>Proje Dizi Konumu: {analysis.project_path}</p>
            <p>Raporlama Tarihi: {analysis.analysis_time.strftime('%d.%m.%Y - %H:%M:%S')}</p>
        </header>

        <div class="score-section">
            <div class="score-circle">{analysis.health_score:.0f}</div>
            <div class="score-details">
                <h2>Sağlık Notu: {analysis.health_status.value}</h2>
                <p>Projenizin kurumsal standartlara, kod kalitesine ve temizlik kurallarına uyumluluk derecesidir.</p>
            </div>
        </div>

        <div class="grid">
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
                <div class="card-value" style="color: #DC2626;">{len(critical_issues)}</div>
            </div>
        </div>

        <h3 class="section-title">🚨 KRİTİK VE YÜKSEK ÖNCELİKLİ SORUNLAR</h3>
        """

        if not critical_issues:
            html += """
            <div class="issue-card severity-info" style="border-left-width: 5px; text-align: center; padding: 30px;">
                <p style="font-weight: bold; color: #16A34A; font-size: 15px; margin: 0;">🎉 Harika! Projenizde hiçbir kritik veya yüksek öncelikli tasarım/güvenlik sorunu bulunamadı.</p>
            </div>
            """
        else:
            for issue in critical_issues:
                badge = self.SEVERITY_BADGES.get(issue.severity, '')
                file_info = f'<span class="path">{issue.file_path.name}</span>' if issue.file_path else ''
                rec_info = f'<div class="issue-rec"><b>💡 Öneri:</b> {issue.recommendation}</div>' if issue.recommendation else ''
                
                html += f"""
                <div class="issue-card severity-{issue.severity.name.lower()}">
                    <div class="issue-header">
                        <span class="issue-title">{issue.title} {file_info}</span>
                        {badge}
                    </div>
                    <div class="issue-desc">{issue.description}</div>
                    {rec_info}
                </div>
                """

        html += """
        <h3 class="section-title">🔍 DİĞER BULGULAR VE İYİLEŞTİRMELER</h3>
        """

        if not other_issues:
            html += """
            <p style="color: #64748B; font-size: 13px;">İyileştirme önerisi bulunmamaktadır.</p>
            """
        else:
            for issue in other_issues:
                # Severity check for warnings (AnalysisResult might have severity or be custom warning)
                sev = getattr(issue, 'severity', Severity.INFO)
                badge = self.SEVERITY_BADGES.get(sev, '')
                file_info = f'<span class="path">{issue.file_path.name}</span>' if getattr(issue, 'file_path', None) else ''
                rec_info = f'<div class="issue-rec"><b>💡 Öneri:</b> {issue.recommendation}</div>' if getattr(issue, 'recommendation', None) else ''
                
                html += f"""
                <div class="issue-card severity-{sev.name.lower()}">
                    <div class="issue-header">
                        <span class="issue-title">{issue.title} {file_info}</span>
                        {badge}
                    </div>
                    <div class="issue-desc">{issue.description}</div>
                    {rec_info}
                </div>
                """

        html += """
    </div>
</body>
</html>
        """
        return html

    def export_report(self, analysis: ProjectAnalysis, output_path: Path) -> bool:
        try:
            content = self.generate_report(analysis)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False