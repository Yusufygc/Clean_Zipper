import QtQuick
import "../singletons"

// Klavye odak göstergesi: üst öğe Tab ile odaklanınca çevresinde belirir (fareyle tıklamada görünmez).
Rectangle {
    anchors.fill: parent
    anchors.margins: -3
    radius: parent.radius + 2
    color: "transparent"
    border.width: 2
    border.color: AppTheme.focusRing
    visible: parent.activeFocus
    z: 100
}
