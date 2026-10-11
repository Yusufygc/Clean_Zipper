import QtQuick
import QtQuick.Layouts
import "../singletons"

Rectangle {
    id: root

    property string title: ""
    property string description: ""
    property string severity: "INFO"
    property string categoryName: ""
    property string fileName: ""
    property string filePath: ""
    property string relPath: ""
    property int line: 0
    property string suggestion: ""
    property string rule: ""
    property string ruleLabel: ""
    property string effort: "S"
    property bool isSecret: false
    property bool approximate: false

    // Kuralı kapatma isteği; kararı Sorunlar sayfası verir (ayarlara yazar ve analizi yeniler)
    signal disableRuleRequested(string rule)

    property bool codeVisible: false
    property string codeText: ""
    readonly property bool hasCode: !isSecret && filePath !== "" && line > 0
    readonly property bool canDisableRule: rule !== "" && !isSecret

    readonly property var severityNames: ({ "CRITICAL": "KRİTİK", "HIGH": "YÜKSEK", "MEDIUM": "ORTA", "LOW": "DÜŞÜK", "INFO": "BİLGİ" })
    readonly property var effortNames: ({ "S": "S (≤ 1 saat)", "M": "M (yarım gün)", "L": "L (1-3 gün)", "XL": "XL (hafta ve üstü)" })

    implicitWidth: parent ? parent.width : 600
    implicitHeight: cardLayout.implicitHeight + 24
    radius: AppTheme.radiusBase
    color: AppTheme.surface
    border.color: AppTheme.border
    border.width: 1

    readonly property color sevColor: {
        var s = severity.toUpperCase()
        if (s === "CRITICAL") return AppTheme.danger
        if (s === "HIGH") return "#EA580C"
        if (s === "MEDIUM") return AppTheme.warning
        if (s === "LOW") return AppTheme.primary
        return AppTheme.success
    }

    // Sol kenar şeridi (Şiddet renk çizgisi)
    Rectangle {
        width: 5
        height: parent.height
        anchors.left: parent.left
        radius: AppTheme.radiusSmall
        color: root.sevColor
    }

    ColumnLayout {
        id: cardLayout
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 12
        anchors.bottomMargin: 12
        spacing: 8

        // 1. Üst Rozet Satırı
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Şiddet Rozeti
            Badge {
                text: root.severityNames[root.severity.toUpperCase()] || root.severity
                textColor: "#FFFFFF"
                badgeColor: root.sevColor
                fontSize: 12
            }

            // Kategori Rozeti
            Badge {
                text: root.categoryName
                textColor: AppTheme.textPrimary
                badgeColor: AppTheme.surfaceHover
                fontSize: 12
                visible: root.categoryName !== ""
            }

            // Efor Rozeti
            Badge {
                text: "Efor: " + (root.effortNames[root.effort] || root.effort)
                textColor: AppTheme.textSecondary
                badgeColor: AppTheme.surfaceActive
                fontSize: 12
            }

            // Kural Kimliği
            Badge {
                text: root.ruleLabel !== "" ? root.ruleLabel : root.rule
                textColor: AppTheme.accent
                badgeColor: AppTheme.tileBg
                borderColor: AppTheme.border
                fontSize: 12
                visible: root.rule !== ""
            }

            // Sözlüksel Yaklaşım Rozeti
            Badge {
                text: "Yaklaşık"
                textColor: AppTheme.warning
                badgeColor: AppTheme.surfaceActive
                fontSize: 12
                visible: root.approximate
            }

            Item { Layout.fillWidth: true }

            // Dosya Konumu & Satır
            RowLayout {
                spacing: 6
                visible: root.fileName !== ""

                SvgIcon {
                    source: AppIcons.document
                    size: 14
                    color: AppTheme.textSecondary
                }

                Text {
                    text: root.isSecret
                          ? (root.fileName + " (Satır gizlendi)")
                          : ((root.relPath !== "" ? root.relPath : root.fileName) + (root.line > 0 ? (" : Satır " + root.line) : ""))
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 420
                    color: root.isSecret ? AppTheme.warning : AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    font.bold: true
                    renderType: Text.NativeRendering
                }
            }
        }

        // 2. Başlık
        Text {
            text: root.title
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeBase
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            renderType: Text.NativeRendering
        }

        // 3. Açıklama
        Text {
            text: root.description
            color: AppTheme.textSecondary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            renderType: Text.NativeRendering
        }

        // 4. Öneri Kutusu (Varsa)
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: sugLayout.implicitHeight + 12
            radius: AppTheme.radiusSmall
            color: AppTheme.codeBg
            border.color: AppTheme.border
            border.width: 1
            visible: root.suggestion !== ""

            RowLayout {
                id: sugLayout
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                SvgIcon {
                    source: AppIcons.check
                    size: 14
                    color: AppTheme.accent
                }

                Text {
                    text: root.suggestion
                    color: AppTheme.accent
                    font.family: AppTheme.fontFamily
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    renderType: Text.NativeRendering
                }
            }
        }

        // 5. Kaynak kodu (istek üzerine okunur; sır içeren bulgularda hiç gösterilmez)
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: codeLabel.implicitHeight + 16
            radius: AppTheme.radiusSmall
            color: AppTheme.bgSecondary
            border.color: AppTheme.border
            border.width: 1
            visible: root.codeVisible

            Text {
                id: codeLabel
                anchors.fill: parent
                anchors.margins: 8
                text: root.codeText !== "" ? root.codeText : "Kaynak satırları okunamadı (dosya taşınmış, çok büyük ya da erişilemiyor)."
                color: root.codeText !== "" ? AppTheme.textPrimary : AppTheme.textMuted
                font.family: "Consolas"
                font.pixelSize: 12
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }
        }

        // 6. Eylemler
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            visible: root.hasCode || root.canDisableRule

            Item { Layout.fillWidth: true }

            CustomButton {
                text: root.codeVisible ? "Kodu Gizle" : "Kodu Göster"
                variant: "secondary"
                implicitHeight: 28
                visible: root.hasCode
                onClicked: {
                    root.codeVisible = !root.codeVisible
                    if (root.codeVisible && root.codeText === "")
                        root.codeText = findingsVM.evidenceFor(root.filePath, root.line, root.isSecret)
                }
            }

            CustomButton {
                text: "Bu Kuralı Kapat"
                variant: "ghost"
                implicitHeight: 28
                visible: root.canDisableRule
                onClicked: root.disableRuleRequested(root.rule)
            }
        }
    }
}
