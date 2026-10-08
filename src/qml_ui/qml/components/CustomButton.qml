import QtQuick
import "../singletons"

Rectangle {
    id: root

    property string text: ""
    property url iconSource: ""
    property int iconSize: 18
    property string variant: "primary" // "primary" | "secondary" | "ghost" | "danger" | "accent"
    property bool enabled: true
    signal clicked()

    implicitWidth: Math.max(contentRow.implicitWidth + 28, 90)
    implicitHeight: 36
    radius: AppTheme.radiusBase

    readonly property bool isHovered: mouseArea.containsMouse && root.enabled
    readonly property bool isPressed: mouseArea.pressed && root.enabled

    // Arka plan rengi belirleme
    color: {
        if (!root.enabled) return AppTheme.isDark ? "#1E293B" : "#E2E8F0"
        if (variant === "primary") {
            return isPressed ? AppTheme.primary : (isHovered ? AppTheme.primaryHover : AppTheme.primary)
        } else if (variant === "accent") {
            return isPressed ? AppTheme.accent : (isHovered ? AppTheme.accentHover : AppTheme.accent)
        } else if (variant === "danger") {
            return isPressed ? "#991B1B" : (isHovered ? "#DC2626" : AppTheme.danger)
        } else if (variant === "secondary") {
            return isPressed ? AppTheme.surfaceActive : (isHovered ? AppTheme.surfaceHover : AppTheme.surface)
        } else { // ghost
            return isPressed ? AppTheme.surfaceActive : (isHovered ? AppTheme.surfaceHover : "transparent")
        }
    }

    // Kenarlık rengi
    border.color: {
        if (!root.enabled) return "transparent"
        if (variant === "secondary") return isHovered ? AppTheme.accent : AppTheme.border
        if (variant === "ghost") return isHovered ? AppTheme.border : "transparent"
        return "transparent"
    }
    border.width: (variant === "secondary" || variant === "ghost") ? 1 : 0

    Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
    Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }

    // Metin & İkon rengi
    readonly property color contentColor: {
        if (!root.enabled) return AppTheme.textMuted
        if (variant === "primary" || variant === "danger") return "#FFFFFF"
        if (variant === "accent") return AppTheme.isDark ? "#0F172A" : "#FFFFFF"
        return AppTheme.textPrimary
    }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 8

        SvgIcon {
            id: btnIcon
            source: root.iconSource
            size: root.iconSize
            color: root.contentColor
            anchors.verticalCenter: parent.verticalCenter
            visible: root.iconSource != ""
        }

        Text {
            id: btnText
            text: root.text
            color: root.contentColor
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeBase
            font.bold: variant === "primary" || variant === "accent" || variant === "danger"
            anchors.verticalCenter: parent.verticalCenter
            renderType: Text.NativeRendering
        }
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
