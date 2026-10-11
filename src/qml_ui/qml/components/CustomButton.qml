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
    signal clicked()

    // Klavye ve erişilebilirlik: Tab ile odaklanır, Enter / Boşluk tıklar, ekran okuyucuya düğme olarak görünür
    // (`enabled`, Item'ın kendi özelliğidir; yeniden tanımlamak temel sınıfı eziyordu)
    activeFocusOnTab: root.enabled
    Accessible.role: Accessible.Button
    Accessible.name: root.text
    Accessible.onPressAction: if (root.enabled) root.clicked()
    Keys.onReturnPressed: if (root.enabled) root.clicked()
    Keys.onEnterPressed: if (root.enabled) root.clicked()
    Keys.onSpacePressed: if (root.enabled) root.clicked()
    FocusRing {}

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
        // Üzerine gelince dolgu değişmez (yalnızca turuncu çerçeve): açılan dolgu beyaz yazının kontrastını düşürürdü
        if (variant === "primary") return isPressed ? AppTheme.startBottom : AppTheme.startTop
        if (variant === "accent") return isPressed ? AppTheme.accentBtnBottom : AppTheme.accentBtnTop
        if (variant === "danger") return isPressed ? AppTheme.dangerBtnBottom : AppTheme.dangerBtnTop
        return isPressed ? AppTheme.btnPressTop : AppTheme.btnTop
    }
    readonly property color bottomColor: {
        if (!root.enabled) return AppTheme.btnDisabledFill
        if (flat) return topColor
        if (variant === "primary") return isPressed ? AppTheme.startTop : AppTheme.startBottom
        if (variant === "accent") return isPressed ? AppTheme.accentBtnTop : AppTheme.accentBtnBottom
        if (variant === "danger") return isPressed ? AppTheme.dangerBtnTop : AppTheme.dangerBtnBottom
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
        if (variant === "accent") return AppTheme.accentBtnBorder
        if (variant === "danger") return AppTheme.dangerBtnBorder
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
