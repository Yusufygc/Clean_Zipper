import QtQuick
import QtQuick.Layouts
import "../singletons"

CardFrame {
    id: root

    property var dataMap: ({})
    property string title: AppStrings.fileDistribution

    padding: 16

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Text {
            text: root.title
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeBase
            font.bold: true
            renderType: Text.NativeRendering
        }

        // Liste Gösterimi (En çok kullanılan ilk 5 uzantı)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6

            Repeater {
                model: {
                    var items = []
                    var total = 0
                    for (var k in root.dataMap) {
                        total += root.dataMap[k]
                    }
                    for (var key in root.dataMap) {
                        var count = root.dataMap[key]
                        var pct = total > 0 ? Math.round((count / total) * 100) : 0
                        items.push({ ext: key || "diğer", count: count, pct: pct })
                    }
                    items.sort(function(a, b) { return b.count - a.count })
                    return items.slice(0, 5)
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Badge {
                        text: modelData.ext
                        textColor: AppTheme.accent
                        badgeColor: AppTheme.surfaceActive
                        fontSize: 11
                        Layout.preferredWidth: 64
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 6
                        radius: 3
                        color: AppTheme.isDark ? "#1E293B" : "#E2E8F0"

                        Rectangle {
                            width: parent.width * (modelData.pct / 100)
                            height: parent.height
                            radius: 3
                            color: AppTheme.primary
                        }
                    }

                    Text {
                        text: "%" + modelData.pct + " (" + modelData.count + ")"
                        color: AppTheme.textSecondary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        Layout.preferredWidth: 70
                        horizontalAlignment: Text.AlignRight
                        renderType: Text.NativeRendering
                    }
                }
            }
        }
    }
}
