import QtQuick
import QtQuick.Layouts
import "../singletons"

// Tek bulgu satırı: kapalıyken ~38 px (şiddet, başlık, kategori, dosya, efor); tıklayınca açıklama, öneri, kod ve eylemler altında açılır.
Rectangle {
    id: root

    property string title: ""
    property string description: ""
    property string severity: "INFO"
    property string categoryName: ""
    property string fileName: ""
    property string filePath: ""
    property string relPath: ""
    property int line: 0
    property string suggestion: ""
    property string rule: ""
    property string ruleLabel: ""
    property string effort: "S"
    property bool isSecret: false
    property bool approximate: false

    property bool grouped: false           // bir grup başlığının altında: girintili
    property bool mixed: false             // "Diğer bulgular" grubunda: kategori ve kural bilgisini satır kendisi taşır
    property bool detailOpen: false        // ayrıntı durumu görünüm modelinde tutulur (kaydırınca kaybolmaz)

    // Satıra tıklama / Enter; kararı Sorunlar sayfası verir. Kuralı kapatma da oradan ayarlara yazılır ve analizi yeniler.
    signal toggleRequested()
    signal disableRuleRequested(string rule)

    property bool codeVisible: false
    property string codeText: ""
    readonly property bool hasCode: !isSecret && filePath !== "" && line > 0
    readonly property bool canDisableRule: rule !== "" && !isSecret
    // Tek kurallı grupta kategori ve kuralı kapatma düğmesi grup başlığındadır
    readonly property bool selfDescribing: !grouped || mixed
    readonly property bool showDisableRule: canDisableRule && selfDescribing

    readonly property var effortNames: ({ "S": "S (≤ 1 saat)", "M": "M (yarım gün)", "L": "L (1-3 gün)", "XL": "XL (hafta ve üstü)" })
    readonly property int rowHeight: 38
    readonly property int indent: grouped ? 30 : 12
    readonly property string locationText: isSecret
        ? (fileName + " (Satır gizlendi)")
        : ((relPath !== "" ? relPath : fileName) + (line > 0 ? (" : " + line) : ""))

    implicitWidth: parent ? parent.width : 600
    implicitHeight: column.implicitHeight
    color: detailOpen || rowArea.containsMouse ? AppTheme.surfaceHover : AppTheme.surface

    // Klavye ve erişilebilirlik: Tab ile odaklanır, Enter / Boşluk ayrıntıyı açar, ekran okuyucu başlığı okur
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: title
    Accessible.description: (detailOpen ? "Ayrıntı açık. " : "Ayrıntı kapalı. ") + locationText
    Accessible.onPressAction: root.toggleRequested()
    Keys.onReturnPressed: root.toggleRequested()
    Keys.onEnterPressed: root.toggleRequested()
    Keys.onSpacePressed: root.toggleRequested()

    Rectangle {                                                        // alt çizgi: liste satırı ayracı
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: AppTheme.borderSubtle
    }

    Rectangle {                                                        // sol şiddet şeridi
        width: 4
        height: parent.height
        color: AppTheme.severityColor(root.severity)
    }

    Rectangle {                                                        // klavye odağı: satırın içinde (liste kırpar)
        anchors.fill: parent
        anchors.margins: 1
        color: "transparent"
        border.width: 2
        border.color: AppTheme.focusRing
        visible: root.activeFocus
        z: 100
    }

    ColumnLayout {
        id: column
        width: parent.width
        spacing: 0

        // 1. Kapalı satır
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.rowHeight

            MouseArea {
                id: rowArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.toggleRequested()
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.indent
                anchors.rightMargin: 12
                spacing: 12

                SvgIcon {
                    source: root.detailOpen ? AppIcons.chevronDown : AppIcons.chevronRight
                    size: 12
                    color: AppTheme.textMuted
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
                    elide: Text.ElideRight
                    Layout.preferredWidth: Math.round(root.width * 0.40)         // başlık ve konum yan yana: ortada boş şerit kalmaz
                    renderType: Text.NativeRendering
                }

                Text {
                    text: root.categoryName
                    visible: root.selfDescribing
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    elide: Text.ElideRight
                    Layout.preferredWidth: 130
                    renderType: Text.NativeRendering
                }

                Text {
                    objectName: "location"
                    text: root.locationText
                    color: root.isSecret ? AppTheme.warning : AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                    renderType: Text.NativeRendering
                }

                Badge {
                    text: root.effort
                    textColor: AppTheme.textSecondary
                    badgeColor: AppTheme.surfaceActive
                    fontSize: 12
                    Layout.preferredWidth: 32
                }
            }
        }

        // 2. Ayrıntı (satır açılınca)
        ColumnLayout {
            id: detail
            visible: root.detailOpen
            Layout.fillWidth: true
            Layout.leftMargin: root.indent + 104                                 // ayrıntı başlıkla aynı hizada
            Layout.rightMargin: 16
            Layout.topMargin: 2
            Layout.bottomMargin: 12
            spacing: 8

            RowLayout {
                spacing: 8

                Badge {
                    text: "Efor: " + (root.effortNames[root.effort] || root.effort)
                    textColor: AppTheme.textSecondary
                    badgeColor: AppTheme.surfaceActive
                    fontSize: 12
                }

                Badge {
                    text: root.ruleLabel !== "" ? root.ruleLabel : root.rule
                    textColor: AppTheme.accent
                    badgeColor: AppTheme.tileBg
                    borderColor: AppTheme.border
                    fontSize: 12
                    visible: root.rule !== "" && root.selfDescribing
                }

                Badge {
                    text: "Yaklaşık"
                    textColor: AppTheme.warning
                    badgeColor: AppTheme.surfaceActive
                    fontSize: 12
                    visible: root.approximate
                }

                Item { Layout.fillWidth: true }
            }

            Text {
                text: root.description
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            // Öneri (grup başlığı ortak öneriyi taşıyorsa satırda boş gelir)
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: sugLayout.implicitHeight + 12
                radius: AppTheme.radiusSmall
                color: AppTheme.codeBg
                border.color: AppTheme.border
                border.width: 1
                visible: root.suggestion !== ""

                RowLayout {
                    id: sugLayout
                    anchors.fill: parent
                    anchors.margins: 8
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

            // Kaynak kodu (istek üzerine okunur; sır içeren bulgularda hiç gösterilmez)
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: codeLabel.implicitHeight + 16
                radius: AppTheme.radiusSmall
                color: AppTheme.bgSecondary
                border.color: AppTheme.border
                border.width: 1
                visible: root.codeVisible

                Text {
                    id: codeLabel
                    anchors.fill: parent
                    anchors.margins: 8
                    text: root.codeText !== "" ? root.codeText : "Kaynak satırları okunamadı (dosya taşınmış, çok büyük ya da erişilemiyor)."
                    color: root.codeText !== "" ? AppTheme.textPrimary : AppTheme.textMuted
                    font.family: "Consolas"
                    font.pixelSize: 12
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: root.hasCode || root.showDisableRule

                Item { Layout.fillWidth: true }

                CustomButton {
                    text: root.codeVisible ? "Kodu Gizle" : "Kodu Göster"
                    variant: "secondary"
                    implicitHeight: 28
                    visible: root.hasCode
                    onClicked: {
                        root.codeVisible = !root.codeVisible
                        if (root.codeVisible && root.codeText === "")
                            root.codeText = findingsVM.evidenceFor(root.filePath, root.line, root.isSecret)
                    }
                }

                CustomButton {
                    text: "Bu Kuralı Kapat"
                    variant: "ghost"
                    implicitHeight: 28
                    visible: root.showDisableRule
                    onClicked: root.disableRuleRequested(root.rule)
                }
            }
        }
    }
}
