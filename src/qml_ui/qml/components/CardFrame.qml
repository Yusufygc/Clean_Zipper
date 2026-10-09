import QtQuick
import "../singletons"

// Kart çerçevesi. İçeriğin ilk çocuğu (genelde bir ColumnLayout / RowLayout) kartın doğal boyutunu belirler:
// kart, içeriğin implicitWidth/implicitHeight değerine iç boşluk eklenerek boyutlanır; böylece Layout içinde
// (RowLayout, ColumnLayout, ScrollView) kart içeriğin altında kalmaz ve diğer öğelerle üst üste binmez.
// Kart Layout tarafından büyütülürse içerik, kartın iç alanını kaplar.
Item {
    id: root

    property color cardBackground: AppTheme.surface
    property color cardBorder: AppTheme.border
    property int padding: 16

    default property alias content: container.data

    readonly property Item firstChild: container.children.length > 0 ? container.children[0] : null

    implicitWidth: (firstChild ? firstChild.implicitWidth : 0) + 2 * padding
    implicitHeight: (firstChild ? firstChild.implicitHeight : 0) + 2 * padding

    Rectangle {
        anchors.fill: parent
        color: root.cardBackground
        border.color: root.cardBorder
        border.width: 1
        radius: AppTheme.radiusCard

        Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
        Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }
    }

    Item {
        id: container
        x: root.padding
        y: root.padding
        width: Math.max(0, root.width - 2 * root.padding)
        height: Math.max(0, root.height - 2 * root.padding)
    }
}
