import QtQuick
import QtQuick.Layouts
import "../singletons"

Rectangle {
    id: root

    property string label: ""
    property int count: 0
    property string severityKey: "ALL"
    property bool isActive: false
    property color activeColor: AppTheme.accent
    signal clicked()

    implicitWidth: pillLayout.implicitWidth + 20
    implicitHeight: 32
    radius: AppTheme.radiusBase

    readonly property bool isHovered: mouseArea.containsMouse

    color: isActive 
           ? AppTheme.surfaceActive 
           : (isHovered ? AppTheme.surfaceHover : AppTheme.surface)
    border.color: isActive ? root.activeColor : AppTheme.border
    border.width: isActive ? 2 : 1

    Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
    Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }

    RowLayout {
        id: pillLayout
        anchors.centerIn: parent
        spacing: 6

        Text {
            text: root.label
            color: root.isActive ? AppTheme.textPrimary : AppTheme.textSecondary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            font.bold: root.isActive
            renderType: Text.NativeRendering
        }

        Badge {
            text: root.count.toString()
            textColor: root.isActive ? "#FFFFFF" : AppTheme.textSecondary
            badgeColor: root.isActive ? root.activeColor : AppTheme.surfaceActive
            fontSize: 10
            bold: true
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
