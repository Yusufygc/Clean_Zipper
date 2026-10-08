import QtQuick
import "../singletons"

Rectangle {
    id: root

    property alias contentChildren: container.data
    default property alias contentData: container.data
    property int padding: 16
    property color cardBackground: AppTheme.surface
    property color cardBorder: AppTheme.border

    color: cardBackground
    border.color: cardBorder
    border.width: 1
    radius: AppTheme.radiusCard

    Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
    Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }

    Item {
        id: container
        anchors.fill: parent
        anchors.margins: root.padding
    }
}
