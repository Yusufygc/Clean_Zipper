import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "singletons"
import "components"
import "views"

ApplicationWindow {
    id: window
    width: 1280
    height: 820
    minimumWidth: 1050
    minimumHeight: 720
    visible: true
    title: AppStrings.appTitle + "  " + AppStrings.appVersion
    color: AppTheme.bg

    // Animasyonlu arka plan rengi geçişi
    Behavior on color { ColorAnimation { duration: AppTheme.animNormal } }

    property int currentTab: 0

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
                spacing: 24

                // Sol: Logo ve Başlık
                RowLayout {
                    spacing: 10

                    SvgIcon {
                        source: AppIcons.shield
                        size: 24
                        color: AppTheme.accent
                    }

                    Text {
                        text: AppStrings.appTitle
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeMedium
                        font.bold: true
                        renderType: Text.NativeRendering
                    }

                    Badge {
                        text: AppStrings.appVersion
                        textColor: AppTheme.accent
                        badgeColor: AppTheme.surfaceActive
                    }
                }

                // Orta: Sekme Menüsü (Segmented Nav)
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 4

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

                            implicitWidth: tabRow.implicitWidth + 24
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

                                SvgIcon {
                                    source: modelData.icon
                                    size: 16
                                    color: tabBtn.isActive 
                                           ? AppTheme.accent 
                                           : (tabBtn.isHovered ? AppTheme.textPrimary : AppTheme.textSecondary)
                                }

                                Text {
                                    text: modelData.title
                                    color: tabBtn.isActive 
                                           ? AppTheme.textPrimary 
                                           : (tabBtn.isHovered ? AppTheme.textPrimary : AppTheme.textSecondary)
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: tabBtn.isActive
                                    renderType: Text.NativeRendering
                                }
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
                        text: appVM.hasProject ? appVM.projectName : AppStrings.openProject
                        iconSource: AppIcons.folder
                        variant: appVM.hasProject ? "secondary" : "primary"
                        onClicked: projectFolderDialog.open()
                    }

                    // Canlı Tema Değiştirme Butonu
                    IconButton {
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
