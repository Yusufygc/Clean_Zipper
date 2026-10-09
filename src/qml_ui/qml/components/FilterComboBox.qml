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

    implicitWidth: 240
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
        contentItem: RowLayout {
            spacing: 8
            Text {
                Layout.fillWidth: true
                text: option.modelData.label
                color: root.current === option.modelData.key ? AppTheme.accent : AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                font.bold: root.current === option.modelData.key
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }
            Text {
                text: option.modelData.count
                color: AppTheme.textMuted
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                font.bold: true
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
            ScrollBar.vertical: ScrollBar { }
        }
        background: Rectangle {
            radius: AppTheme.radiusBase
            color: AppTheme.surfaceElevated
            border.color: AppTheme.border
            border.width: 1
        }
    }
}
