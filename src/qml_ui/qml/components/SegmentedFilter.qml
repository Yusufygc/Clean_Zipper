import QtQuick
import QtQuick.Layouts
import "../singletons"

// Tek çerçeveli, bitişik seçenekli süzgeç (ör. şiddet düzeyi). Seçenekler: [{key, label, count, color}]
Rectangle {
    id: root

    property var options: []
    property string current: "ALL"
    signal selected(string key)

    implicitHeight: 36
    implicitWidth: row.implicitWidth + 8
    radius: AppTheme.radiusBase
    color: AppTheme.bgSecondary
    border.color: AppTheme.border
    border.width: 1

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 2

        Repeater {
            model: root.options

            Rectangle {
                id: segment
                readonly property bool isActive: root.current === modelData.key
                readonly property bool isHovered: area.containsMouse

                implicitWidth: content.implicitWidth + 20
                implicitHeight: 28
                radius: AppTheme.radiusSmall + 2
                color: isActive ? AppTheme.surfaceActive : (isHovered ? AppTheme.surfaceHover : "transparent")
                Behavior on color { ColorAnimation { duration: AppTheme.animFast } }

                RowLayout {
                    id: content
                    anchors.centerIn: parent
                    spacing: 6

                    Rectangle {
                        visible: modelData.key !== "ALL"
                        Layout.preferredWidth: 8
                        Layout.preferredHeight: 8
                        radius: 4
                        color: modelData.color
                    }
                    Text {
                        text: modelData.label
                        color: segment.isActive ? AppTheme.textPrimary : AppTheme.textSecondary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        font.bold: segment.isActive
                        renderType: Text.NativeRendering
                    }
                    Text {
                        text: modelData.count
                        color: segment.isActive ? AppTheme.accent : AppTheme.textMuted
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        font.bold: true
                        renderType: Text.NativeRendering
                    }
                }

                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selected(modelData.key)
                }
            }
        }
    }
}
