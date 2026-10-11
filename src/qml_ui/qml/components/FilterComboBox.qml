import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../singletons"

// Açılır liste süzgeci. Seçenekler: [{key, label, count}]; seçili anahtar `current`, seçim `picked(key)` ile bildirilir.
ComboBox {
    id: root

    property string caption: ""
    property string current: "ALL"
    signal picked(string key)

    // Kapalı kutu ile açılan liste aynı genişliktedir; genişlik en uzun adın genişliğinden hesaplanır
    implicitWidth: Math.max(160, labelWidth + 28 + 2 * rowPadding + 8,
                            12 + captionMetrics.width + 6 + labelWidth + 8 + 16 + 12)
    implicitHeight: 36
    model: []
    textRole: "label"
    currentIndex: {
        for (var i = 0; i < model.length; i++) {
            if (model[i].key === current) return i
        }
        return 0
    }
    onActivated: function(index) { root.picked(model[index].key) }

    background: Rectangle {
        radius: AppTheme.radiusBase
        color: root.hovered || root.popup.visible ? AppTheme.surfaceHover : AppTheme.surface
        border.color: root.popup.visible ? AppTheme.accent : AppTheme.border
        border.width: 1
    }

    contentItem: RowLayout {
        spacing: 6

        Text {
            Layout.leftMargin: 12
            text: root.caption
            visible: root.caption !== ""
            color: AppTheme.textMuted
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            renderType: Text.NativeRendering
        }
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: root.caption === "" ? 12 : 0
            text: root.displayText
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            font.bold: true
            elide: Text.ElideRight
            renderType: Text.NativeRendering
        }
        Text {
            Layout.rightMargin: 12
            text: "▾"
            color: AppTheme.textSecondary
            font.pixelSize: AppTheme.fontSizeBase
            renderType: Text.NativeRendering
        }
    }

    indicator: Item { }

    // Açılan listede ad solda, sayı sağda, aralarında az boşluk
    property real labelWidth: 0
    readonly property int rowPadding: 14
    onModelChanged: labelWidth = 0

    TextMetrics {
        id: captionMetrics
        text: root.caption
        font.family: AppTheme.fontFamily
        font.pixelSize: AppTheme.fontSizeSmall
    }

    Repeater {
        model: root.model
        delegate: Text {
            visible: false
            text: modelData.label
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            font.bold: true
            Component.onCompleted: root.labelWidth = Math.max(root.labelWidth, implicitWidth)
        }
    }

    delegate: ItemDelegate {
        id: option
        required property var modelData
        required property int index
        width: root.width - 8
        height: 32
        highlighted: root.highlightedIndex === index

        background: Rectangle {
            radius: AppTheme.radiusSmall
            color: option.highlighted ? AppTheme.surfaceActive : "transparent"
        }
        // Ad sola, sayı sağa yaslı; iki yanda eşit iç boşluk
        contentItem: RowLayout {
            spacing: 12
            Text {
                Layout.fillWidth: true
                Layout.leftMargin: root.rowPadding - 4
                text: option.modelData.label
                color: root.current === option.modelData.key ? AppTheme.accent : AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                font.bold: root.current === option.modelData.key
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }
            Text {
                Layout.rightMargin: root.rowPadding - 4
                text: option.modelData.count
                color: AppTheme.textMuted
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                font.bold: true
                horizontalAlignment: Text.AlignRight
                renderType: Text.NativeRendering
            }
        }
    }

    popup: Popup {
        y: root.height + 4
        width: root.width
        height: Math.min(list.contentHeight + 8, 340)
        padding: 4

        contentItem: ListView {
            id: list
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollBar.vertical: ThemedScrollBar { }
        }
        background: Rectangle {
            radius: AppTheme.radiusBase
            color: AppTheme.surfaceElevated
            border.color: AppTheme.border
            border.width: 1
        }
    }
}
