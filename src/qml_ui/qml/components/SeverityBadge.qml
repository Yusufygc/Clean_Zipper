import QtQuick
import "../singletons"

// Şiddet rozeti: Türkçe ad ve şiddet rengi tek yerde (satır, grup başlığı); yazı rengi her zeminle en az 4,5:1.
Badge {
    property string severity: "INFO"

    readonly property var severityNames: ({ "CRITICAL": "KRİTİK", "HIGH": "YÜKSEK", "MEDIUM": "ORTA", "LOW": "DÜŞÜK", "INFO": "BİLGİ" })

    text: severityNames[severity.toUpperCase()] || severity
    textColor: AppTheme.onSeverity
    badgeColor: AppTheme.severityColor(severity)
    fontSize: 12
}
