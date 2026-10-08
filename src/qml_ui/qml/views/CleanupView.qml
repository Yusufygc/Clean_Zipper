import QtQuick
import QtQuick.Layouts
import "../singletons"
import "../components"

Item {
    id: root

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16

        SvgIcon {
            source: AppIcons.trash
            size: 48
            color: AppTheme.danger
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: AppStrings.tabCleanup
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeTitle
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: AppStrings.cleanupSubtitle
            color: AppTheme.textSecondary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeBase
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
