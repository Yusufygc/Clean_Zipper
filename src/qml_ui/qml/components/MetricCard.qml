import QtQuick
import QtQuick.Layouts
import "../singletons"

CardFrame {
    id: root

    property string title: ""
    property string value: "—"
    property string subtitle: ""
    property url iconSource: ""
    property color iconColor: AppTheme.accent
    property color iconBg: AppTheme.isDark ? "#111827" : "#F1F5F9"

    padding: 16
    implicitHeight: 92

    RowLayout {
        anchors.fill: parent
        spacing: 16

        // İkon Çerçevesi
        Rectangle {
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            radius: AppTheme.radiusBase
            color: root.iconBg
            border.color: AppTheme.border
            border.width: 1

            SvgIcon {
                anchors.centerIn: parent
                source: root.iconSource
                size: 22
                color: root.iconColor
            }
        }

        // Metin Bilgileri
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: root.title
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Text {
                text: root.value
                color: AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeTitle
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Text {
                text: root.subtitle
                color: AppTheme.textMuted
                font.family: AppTheme.fontFamily
                font.pixelSize: 12
                visible: root.subtitle !== ""
                elide: Text.ElideRight
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }
        }
    }
}
