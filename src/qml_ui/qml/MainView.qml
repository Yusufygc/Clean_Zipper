import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "singletons"
import "components"
import "views"

ApplicationWindow {
    id: window
    // Açılış boyutu ekrana göre belirlenir (Component.onCompleted); bu değerler yedektir
    width: 1280
    height: 820
    minimumWidth: Math.min(900, Screen.desktopAvailableWidth)       // küçük ekranda ekrandan büyük asgari boyut olmaz
    minimumHeight: Math.min(600, Screen.desktopAvailableHeight)
    visible: true
    title: AppStrings.appTitle + "  " + AppStrings.appVersion
    color: AppTheme.bg

    // Animasyonlu arka plan rengi geçişi
    Behavior on color { ColorAnimation { duration: AppTheme.animNormal } }

    property int currentTab: 0

    // Duyarlı başlık: pencere daraldıkça önce başlık metni ve sürüm rozeti, sonra pasif sekme yazıları gizlenir;
    // sekmeler, proje düğmesi ve tema düğmesi hiçbir genişlikte pencere dışına taşmaz.
    readonly property bool compactHeader: width < 1400       // başlık metni + sürüm rozeti gizli
    readonly property bool iconOnlyTabs: width < 1120        // yalnızca etkin sekmenin yazısı görünür

    Component.onCompleted: {
        // Açılış boyutu: kullanılabilir ekran alanının %85'i, makul sınırlar içinde; ekranın ortasında
        width = Math.round(Math.min(Math.max(Screen.desktopAvailableWidth * 0.85, minimumWidth), 1600, Screen.desktopAvailableWidth))
        height = Math.round(Math.min(Math.max(Screen.desktopAvailableHeight * 0.85, minimumHeight), 1000, Screen.desktopAvailableHeight))
        x = Math.round((Screen.desktopAvailableWidth - width) / 2)
        y = Math.round((Screen.desktopAvailableHeight - height) / 2)
    }

    // Klasör Seçim Diyaloğu
    FolderDialog {
        id: projectFolderDialog
        title: AppStrings.openProject
        currentFolder: appVM.projectPath !== "" ? ("file:///" + appVM.projectPath) : ""
        onAccepted: {
            appVM.setProjectPath(selectedFolder.toString())
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ══════════════════════════════════════════════════════════
        // 1. ÜST BAŞLIK & GEZİNME ÇUBUĞU (HEADER & NAVIGATION)
        // ══════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: AppTheme.surfaceElevated
            border.color: AppTheme.border
            border.width: 1

            Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
            Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: window.iconOnlyTabs ? 6 : (window.compactHeader ? 10 : 24)

                // Sol: Logo ve Başlık
                RowLayout {
                    spacing: 10

                    SvgIcon {
                        source: AppIcons.shield
                        size: 24
                        color: AppTheme.accent
                    }

                    Text {
                        visible: !window.compactHeader
                        text: AppStrings.appTitle
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeMedium
                        font.bold: true
                        renderType: Text.NativeRendering
                    }

                    Badge {
                        visible: !window.compactHeader
                        text: AppStrings.appVersion
                        textColor: AppTheme.accent
                        badgeColor: AppTheme.surfaceActive
                    }
                }

                // Orta: Sekme Menüsü (Segmented Nav)
                RowLayout {
                    objectName: "tabNav"
                    Layout.alignment: Qt.AlignHCenter
                    spacing: window.compactHeader ? 2 : 4

                    Repeater {
                        model: [
                            { idx: 0, title: AppStrings.tabDashboard, icon: AppIcons.dashboard },
                            { idx: 1, title: AppStrings.tabFindings,  icon: AppIcons.shield },
                            { idx: 2, title: AppStrings.tabArchive,   icon: AppIcons.archive },
                            { idx: 3, title: AppStrings.tabCleanup,   icon: AppIcons.trash },
                            { idx: 4, title: AppStrings.tabSettings,  icon: AppIcons.settings }
                        ]

                        Rectangle {
                            id: tabBtn
                            readonly property bool isActive: window.currentTab === modelData.idx
                            readonly property bool isHovered: tabMouse.containsMouse

                            implicitWidth: tabRow.implicitWidth
                            implicitHeight: 34
                            radius: AppTheme.radiusBase

                            color: isActive 
                                   ? AppTheme.surfaceActive 
                                   : (isHovered ? AppTheme.surfaceHover : "transparent")

                            border.color: isActive ? AppTheme.border : "transparent"
                            border.width: 1

                            Behavior on color { ColorAnimation { duration: AppTheme.animFast } }

                            RowLayout {
                                id: tabRow
                                anchors.centerIn: parent
                                spacing: 8

                                // İç boşluk satırın kendi içinde: sekme genişliği düzey değişiminden bağımsız hesaplanır
                                Item { Layout.preferredWidth: window.iconOnlyTabs ? 0 : (window.compactHeader ? 2 : 4) }

                                SvgIcon {
                                    source: modelData.icon
                                    size: 16
                                    color: tabBtn.isActive 
                                           ? AppTheme.accent 
                                           : (tabBtn.isHovered ? AppTheme.textPrimary : AppTheme.textSecondary)
                                }

                                Text {
                                    visible: tabBtn.isActive || !window.iconOnlyTabs
                                    text: modelData.title
                                    color: tabBtn.isActive 
                                           ? AppTheme.textPrimary 
                                           : (tabBtn.isHovered ? AppTheme.textPrimary : AppTheme.textSecondary)
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: tabBtn.isActive
                                    renderType: Text.NativeRendering
                                }

                                Item { Layout.preferredWidth: window.iconOnlyTabs ? 0 : (window.compactHeader ? 2 : 4) }
                            }

                            MouseArea {
                                id: tabMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: window.currentTab = modelData.idx
                            }
                        }
                    }
                }

                Item { Layout.fillWidth: true } // Yay

                // Sağ: Proje Açma & Tema Değiştirme
                RowLayout {
                    spacing: 12

                    // Proje Seçim Butonu
                    CustomButton {
                        objectName: "projectButton"
                        // Uzun proje adı başlığı taşırmasın
                        text: appVM.hasProject
                              ? (appVM.projectName.length > 22 ? appVM.projectName.slice(0, 21) + "…" : appVM.projectName)
                              : AppStrings.openProject
                        iconSource: AppIcons.folder
                        variant: appVM.hasProject ? "secondary" : "primary"
                        onClicked: projectFolderDialog.open()
                    }

                    // Canlı Tema Değiştirme Butonu
                    IconButton {
                        objectName: "themeButton"
                        iconSource: AppTheme.isDark ? AppIcons.sun : AppIcons.moon
                        iconColor: AppTheme.accent
                        onClicked: AppTheme.toggleTheme()
                    }
                }
            }
        }

        // ══════════════════════════════════════════════════════════
        // 2. ANA İÇERİK ALANI (VIEWS STACK)
        // ══════════════════════════════════════════════════════════
        StackLayout {
            id: mainStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.currentTab

            DashboardView {
                id: dashView
            }

            FindingsView {
                id: findingsView
            }

            ArchiveView {
                id: archiveView
            }

            CleanupView {
                id: cleanupView
            }

            SettingsView {
                id: settingsView
            }
        }

        // ══════════════════════════════════════════════════════════
        // 3. ALT DURUM ÇUBUĞU (STATUS BAR)
        // ══════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            color: AppTheme.surfaceElevated
            border.color: AppTheme.border
            border.width: 1

            Behavior on color { ColorAnimation { duration: AppTheme.animFast } }
            Behavior on border.color { ColorAnimation { duration: AppTheme.animFast } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                SvgIcon {
                    source: AppIcons.info
                    size: 14
                    color: AppTheme.accent
                }

                Text {
                    text: appVM.statusText
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: appVM.hasProject ? appVM.projectPath : AppStrings.noProjectSelected
                    color: AppTheme.textMuted
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 400
                    renderType: Text.NativeRendering
                }
            }
        }
    }
}
