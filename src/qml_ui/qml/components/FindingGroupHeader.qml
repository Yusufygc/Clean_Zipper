import QtQuick
import QtQuick.Layouts
import "../singletons"

// Aynı kuralın bulgularını toplayan başlık: şiddet, kural adı, sayı, kategori; açıkken ortak öneri bir kez gösterilir.
Item {
    id: root

    property string title: ""
    property string severity: "INFO"
    property string categoryName: ""
    property string suggestion: ""         // grubun tüm bulguları için ortak öneri (farklıysa boş)
    property string rule: ""
    property int count: 0
    property bool expanded: false
    property bool collapsible: true        // süzgeç açıkken gruplar katlanamaz
    property bool canDisable: false

    signal toggleRequested()
    signal disableRuleRequested(string rule)

    readonly property int gap: 10          // gruplar arası boşluk
    readonly property int bandHeight: 36

    implicitWidth: parent ? parent.width : 600
    implicitHeight: gap + column.implicitHeight

    activeFocusOnTab: collapsible
    Accessible.role: Accessible.Button
    Accessible.name: title + ", " + count + " bulgu"
    Accessible.description: expanded ? "Grup açık" : "Grup kapalı"
    Accessible.onPressAction: if (collapsible) root.toggleRequested()
    Keys.onReturnPressed: if (collapsible) root.toggleRequested()
    Keys.onEnterPressed: if (collapsible) root.toggleRequested()
    Keys.onSpacePressed: if (collapsible) root.toggleRequested()

    ColumnLayout {
        id: column
        y: root.gap
        width: parent.width
        spacing: 0

        Rectangle {
            id: band
            Layout.fillWidth: true
            Layout.preferredHeight: root.bandHeight
            color: bandArea.containsMouse && root.collapsible ? AppTheme.surfaceActive : AppTheme.surfaceHover
            border.color: AppTheme.border
            border.width: 1

            MouseArea {
                id: bandArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: root.collapsible ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: if (root.collapsible) root.toggleRequested()
            }

            Rectangle {
                width: 4
                height: parent.height
                color: AppTheme.severityColor(root.severity)
            }

            Rectangle {                                                // klavye odağı
                anchors.fill: parent
                anchors.margins: 1
                color: "transparent"
                border.width: 2
                border.color: AppTheme.focusRing
                visible: root.activeFocus
                z: 100
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 8
                spacing: 12

                SvgIcon {
                    source: root.expanded ? AppIcons.chevronDown : AppIcons.chevronRight
                    size: 12
                    color: AppTheme.textPrimary
                    opacity: root.collapsible ? 1.0 : 0.35
                }

                SeverityBadge {
                    severity: root.severity
                    Layout.preferredWidth: 68
                }

                Text {
                    text: root.title
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeBase
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.maximumWidth: Math.round(root.width * 0.55)
                    renderType: Text.NativeRendering
                }

                Badge {                                                // sayı başlığın hemen yanında: okuma akışı bozulmaz
                    objectName: "groupCount"
                    text: root.count + " bulgu"
                    textColor: AppTheme.textPrimary
                    badgeColor: AppTheme.surface
                    borderColor: AppTheme.border
                    fontSize: 12
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: root.categoryName
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    elide: Text.ElideRight
                    Layout.preferredWidth: 130
                    renderType: Text.NativeRendering
                }

                Item {                                                 // sabit genişlik: düğme olmayan başlıklarda sütunlar kaymaz
                    Layout.preferredWidth: 124
                    Layout.preferredHeight: 26

                    CustomButton {
                        anchors.fill: parent
                        text: "Bu Kuralı Kapat"
                        variant: "ghost"
                        implicitHeight: 26
                        visible: root.canDisable
                        onClicked: root.disableRuleRequested(root.rule)
                    }
                }
            }
        }

        // Ortak öneri: grup açıkken bir kez
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: sugLayout.implicitHeight + 12
            color: AppTheme.codeBg
            border.color: AppTheme.border
            border.width: 1
            visible: root.expanded && root.suggestion !== ""

            RowLayout {
                id: sugLayout
                anchors.fill: parent
                anchors.margins: 8
                anchors.leftMargin: 14
                spacing: 8

                SvgIcon {
                    source: AppIcons.check
                    size: 14
                    color: AppTheme.accent
                }

                Text {
                    text: root.suggestion
                    color: AppTheme.accent
                    font.family: AppTheme.fontFamily
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    renderType: Text.NativeRendering
                }
            }
        }
    }
}
