import QtQuick
import QtQuick.Layouts
import "../singletons"

Item {
    id: root

    property string title: ""
    property int score: 0

    implicitHeight: 28
    implicitWidth: 200

    readonly property color barColor: {
        if (score >= 80) return AppTheme.success
        if (score >= 50) return AppTheme.warning
        return AppTheme.danger
    }

    RowLayout {
        anchors.fill: parent
        spacing: 10

        Text {
            text: root.title
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            font.bold: true
            Layout.preferredWidth: 100
            elide: Text.ElideRight
            renderType: Text.NativeRendering
        }

        // İlerleme çubuğu
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 8
            radius: 4
            color: AppTheme.trackBg

            Rectangle {
                width: parent.width * Math.min(Math.max(root.score, 0), 100) / 100
                height: parent.height
                radius: 4
                color: root.barColor

                Behavior on width {
                    NumberAnimation { duration: 400; easing.type: Easing.OutQuad }
                }
            }
        }

        Text {
            text: root.score.toString()
            color: root.barColor
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            font.bold: true
            Layout.preferredWidth: 28
            horizontalAlignment: Text.AlignRight
            renderType: Text.NativeRendering
        }
    }
}
