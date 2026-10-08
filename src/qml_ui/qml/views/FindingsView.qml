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
            source: AppIcons.shield
            size: 48
            color: AppTheme.info
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: AppStrings.tabFindings
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeTitle
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: AppStrings.searchPlaceholder
            color: AppTheme.textSecondary
            font.family: AppTheme.fontFamily
            font.pixelSize: AppTheme.fontSizeBase
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
