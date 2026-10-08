import QtQuick
import "../singletons"

Rectangle {
    id: root

    property string text: ""
    property color textColor: AppTheme.textPrimary
    property color badgeColor: AppTheme.surfaceHover
    property color borderColor: "transparent"
    property int fontSize: AppTheme.fontSizeSmall
    property bool bold: true

    implicitWidth: badgeText.implicitWidth + 16
    implicitHeight: Math.max(badgeText.implicitHeight + 8, 22)
    radius: height / 2

    color: badgeColor
    border.color: borderColor
    border.width: borderColor !== "transparent" ? 1 : 0

    Text {
        id: badgeText
        anchors.centerIn: parent
        text: root.text
        color: root.textColor
        font.family: AppTheme.fontFamily
        font.pixelSize: root.fontSize
        font.bold: root.bold
        renderType: Text.NativeRendering
    }
}
