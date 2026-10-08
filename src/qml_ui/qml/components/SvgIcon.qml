import QtQuick
import QtQuick.Effects

Item {
    id: root

    property url source: ""
    property int size: 20
    property color color: "#FFFFFF"

    implicitWidth: size
    implicitHeight: size

    Image {
        id: iconImage
        anchors.fill: parent
        source: root.source
        sourceSize.width: root.size * 2
        sourceSize.height: root.size * 2
        fillMode: Image.PreserveAspectFit
        smooth: true
        visible: false
    }

    MultiEffect {
        anchors.fill: iconImage
        source: iconImage
        colorization: 1.0
        colorizationColor: root.color
        visible: root.source != ""
    }
}
