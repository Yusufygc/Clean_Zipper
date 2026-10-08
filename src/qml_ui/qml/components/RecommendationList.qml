import QtQuick
import QtQuick.Layouts
import "../singletons"

CardFrame {
    id: root

    property var recommendations: []

    padding: 16

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            spacing: 8
            SvgIcon {
                source: AppIcons.check
                size: 16
                color: AppTheme.success
            }
            Text {
                text: AppStrings.recommendations
                color: AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeBase
                font.bold: true
                renderType: Text.NativeRendering
            }
        }

        // Eğer öneri yoksa
        Text {
            text: "Sistemde öncelikli bir aksiyon gereksinimi bulunmuyor."
            color: AppTheme.textSecondary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeSmall
            visible: root.recommendations.length === 0
            Layout.alignment: Qt.AlignHCenter
            renderType: Text.NativeRendering
        }

        // Öneriler Listesi (en fazla 4 adet)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            visible: root.recommendations.length > 0

            Repeater {
                model: root.recommendations.slice(0, 4)

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: recCol.implicitHeight + 16
                    radius: AppTheme.radiusSmall
                    color: AppTheme.surfaceHover
                    border.color: AppTheme.border
                    border.width: 1

                    RowLayout {
                        id: recCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 12

                        Rectangle {
                            Layout.preferredWidth: 4
                            Layout.fillHeight: true
                            radius: 2
                            color: {
                                var prio = (modelData.priority || "").toUpperCase()
                                if (prio.indexOf("YÜKSEK") !== -1 || prio.indexOf("HIGH") !== -1) return AppTheme.danger
                                if (prio.indexOf("ORTA") !== -1 || prio.indexOf("MEDIUM") !== -1) return AppTheme.warning
                                return AppTheme.accent
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            Text {
                                text: modelData.title || ""
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: modelData.description || ""
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                renderType: Text.NativeRendering
                            }
                        }
                    }
                }
            }
        }
    }
}
