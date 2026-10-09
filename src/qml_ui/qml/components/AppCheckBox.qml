import QtQuick
import QtQuick.Controls
import "../singletons"

// Koyu temada da görünür onay kutusu. Etiket ayrı bir Text ile yazılır (yan yana yerleşim için).
CheckBox {
    id: control

    implicitWidth: 24
    implicitHeight: 24
    padding: 0
    spacing: 0

    indicator: Rectangle {
        implicitWidth: 20
        implicitHeight: 20
        x: (control.width - width) / 2
        y: (control.height - height) / 2
        radius: 5
        color: control.checked ? AppTheme.accent : (control.hovered ? AppTheme.surfaceHover : AppTheme.bgSecondary)
        border.color: control.checked || control.hovered || control.visualFocus ? AppTheme.accent : AppTheme.border
        border.width: 1

        Behavior on color { ColorAnimation { duration: AppTheme.animFast } }

        Text {
            anchors.centerIn: parent
            text: "✓"
            visible: control.checked
            color: AppTheme.textInverse
            font.pixelSize: 14
            font.bold: true
        }
    }

    contentItem: Item {}
}
