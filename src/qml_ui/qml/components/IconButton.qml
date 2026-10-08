import QtQuick
import "../singletons"

Rectangle {
    id: root

    property url iconSource: ""
    property int iconSize: 18
    property color iconColor: isHovered ? AppTheme.accent : AppTheme.textSecondary
    property string tooltip: ""
    property bool enabled: true
    signal clicked()

    implicitWidth: 36
    implicitHeight: 36
    radius: AppTheme.radiusBase

    readonly property bool isHovered: mouseArea.containsMouse && root.enabled
    readonly property bool isPressed: mouseArea.pressed && root.enabled

    color: isPressed ? AppTheme.surfaceActive : (isHovered ? AppTheme.surfaceHover : "transparent")
    border.color: isHovered ? AppTheme.border : "transparent"
    border.width: 1

    Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
    Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }

    SvgIcon {
        anchors.centerIn: parent
        source: root.iconSource
        size: root.iconSize
        color: root.iconColor
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.enabled) root.clicked()
        }
    }
}
