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
    property int line: 0
    property string suggestion: ""
    property string rule: ""
    property string effort: "S"
    property bool isSecret: false
    property bool approximate: false

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
                text: root.severity
                textColor: "#FFFFFF"
                badgeColor: root.sevColor
                fontSize: 10
            }

            // Kategori Rozeti
            Badge {
                text: root.categoryName
                textColor: AppTheme.textPrimary
                badgeColor: AppTheme.surfaceHover
                fontSize: 10
                visible: root.categoryName !== ""
            }

            // Efor Rozeti
            Badge {
                text: "Efor: " + root.effort
                textColor: AppTheme.textSecondary
                badgeColor: AppTheme.surfaceActive
                fontSize: 10
            }

            // Kural Kimliği
            Badge {
                text: root.rule
                textColor: AppTheme.accent
                badgeColor: AppTheme.isDark ? "#111827" : "#F1F5F9"
                borderColor: AppTheme.border
                fontSize: 10
                visible: root.rule !== ""
            }

            // Sözlüksel Yaklaşım Rozeti
            Badge {
                text: "Yaklaşık"
                textColor: AppTheme.warning
                badgeColor: AppTheme.surfaceActive
                fontSize: 10
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
                          : (root.fileName + (root.line > 0 ? (" : Satır " + root.line) : ""))
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
            color: AppTheme.isDark ? "#111827" : "#F8FAFC"
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
                    font.pixelSize: 11
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    renderType: Text.NativeRendering
                }
            }
        }
    }
}
