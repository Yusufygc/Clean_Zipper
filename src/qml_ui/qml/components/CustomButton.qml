import QtQuick
import "../singletons"

// XP düğmesi: gradyanlı, küçük yarıçaplı; üzerine gelince turuncu çerçeve, basılınca ters gradyan.
// Birincil eylem yeşil ("Başlat" düğmesi), vurgu mavi, tehlike kırmızı, ikincil bej, hayalet düz.
Rectangle {
    id: root

    property string text: ""
    property url iconSource: ""
    property int iconSize: 18
    property string variant: "primary" // "primary" | "secondary" | "ghost" | "danger" | "accent"
    property bool enabled: true
    signal clicked()

    implicitWidth: Math.max(contentRow.implicitWidth + 28, 90)
    implicitHeight: 34
    radius: AppTheme.radiusBase

    readonly property bool isHovered: mouseArea.containsMouse && root.enabled
    readonly property bool isPressed: mouseArea.pressed && root.enabled
    readonly property bool flat: variant === "ghost"

    // Gradyan uçları
    readonly property color topColor: {
        if (!root.enabled) return AppTheme.btnDisabledFill
        if (flat) return isPressed ? AppTheme.surfaceActive : (isHovered ? AppTheme.surfaceHover : "transparent")
        if (variant === "primary") return isPressed ? AppTheme.startBottom : (isHovered ? Qt.lighter(AppTheme.startTop, 1.08) : AppTheme.startTop)
        if (variant === "accent") return isPressed ? "#1F5FD6" : (isHovered ? "#7DB3FF" : "#5EA3FF")
        if (variant === "danger") return isPressed ? "#C8401F" : (isHovered ? "#F59A82" : "#F0876B")
        return isPressed ? AppTheme.btnPressTop : AppTheme.btnTop
    }
    readonly property color bottomColor: {
        if (!root.enabled) return AppTheme.btnDisabledFill
        if (flat) return topColor
        if (variant === "primary") return isPressed ? AppTheme.startTop : AppTheme.startBottom
        if (variant === "accent") return isPressed ? "#5EA3FF" : "#1F5FD6"
        if (variant === "danger") return isPressed ? "#F0876B" : "#C8401F"
        return isPressed ? AppTheme.btnPressBottom : AppTheme.btnBottom
    }

    gradient: Gradient {
        GradientStop { position: 0.0; color: root.topColor }
        GradientStop { position: 1.0; color: root.bottomColor }
    }

    border.width: flat ? (isHovered ? 1 : 0) : 1
    border.color: {
        if (!root.enabled) return AppTheme.btnDisabledBorder
        if (flat) return AppTheme.border
        if (isHovered && !isPressed) return AppTheme.btnHoverBorder       // XP: üzerine gelince turuncu çerçeve
        if (variant === "primary") return AppTheme.startBorder
        if (variant === "accent") return "#0A3A99"
        if (variant === "danger") return "#8E2A12"
        return AppTheme.borderStrong
    }

    // Metin & ikon rengi
    readonly property color contentColor: {
        if (!root.enabled) return AppTheme.btnDisabledText
        if (variant === "primary" || variant === "danger" || variant === "accent") return "#FFFFFF"
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
            font.bold: root.variant !== "ghost"
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
