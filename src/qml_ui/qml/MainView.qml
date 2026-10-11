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
    title: AppStrings.appTitle + "  v" + updateVM.currentVersion
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
        installVM.requestPromptIfNeeded()
    }

    // İndirilen exe kurulu değilse açılışta kurma önerisi (kurulu kopya başlatılır, bu kopya kapanır)
    InstallDialog { id: installDialog }

    Connections {
        target: installVM
        function onPromptRequested() { installDialog.open() }
        function onFinished() { Qt.quit() }
    }

    // Yeni sürüm bulununca açılan pencere (açılışta sessiz denetim; ayarlardan elle denetim)
    UpdateDialog { id: updateDialog }

    Connections {
        target: updateVM
        function onPopupRequested() { updateDialog.open() }
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
        // Windows XP (Luna): mavi gradyan başlık; seçili sekme içerikle aynı bej, üstünde turuncu çizgi
        // ══════════════════════════════════════════════════════════
        Rectangle {
            id: header
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            border.width: 0

            gradient: Gradient {
                GradientStop { position: 0.0; color: AppTheme.titleTop }
                GradientStop { position: 0.45; color: AppTheme.titleMid }
                GradientStop { position: 1.0; color: AppTheme.titleBottom }
            }

            // Sekmelerin altındaki ayırıcı çizgi; seçili sekme bunu kapatarak içeriğe kaynaşır
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: AppTheme.border
                z: 0
            }

            Item {
                id: headerBar
                anchors.fill: parent
                readonly property int gap: window.iconOnlyTabs ? 6 : (window.compactHeader ? 10 : 24)

                // Sol: Logo ve Başlık
                RowLayout {
                    id: headerLeft
                    anchors.left: parent.left
                    anchors.leftMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    SvgIcon {
                        source: AppIcons.shield
                        size: 24
                        color: AppTheme.titleText
                    }

                    Text {
                        visible: !window.compactHeader
                        text: AppStrings.appTitle
                        color: AppTheme.titleText
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeMedium
                        font.bold: true
                        style: Text.Raised                      // XP başlık yazısındaki hafif gölge
                        styleColor: "#0A2A7A"
                        renderType: Text.NativeRendering
                    }

                    Badge {
                        visible: !window.compactHeader
                        text: "v" + updateVM.currentVersion
                        textColor: AppTheme.titleText
                        badgeColor: Qt.rgba(1, 1, 1, 0.2)
                        borderColor: Qt.rgba(1, 1, 1, 0.45)
                    }
                }

                // Orta: XP sekmeleri; çubuğun alt kenarına oturur, yer yoksa komşularına çarpmayacak kadar kayar
                RowLayout {
                    id: tabNav
                    objectName: "tabNav"
                    anchors.bottom: parent.bottom
                    x: Math.max(headerLeft.x + headerLeft.width + headerBar.gap,
                                Math.min((headerBar.width - width) / 2, headerRight.x - width - headerBar.gap))
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
                            implicitHeight: 36
                            radius: 0
                            topLeftRadius: 5
                            topRightRadius: 5
                            z: isActive ? 2 : 1

                            // Klavye ve erişilebilirlik: Tab ile odaklanır, Enter / Boşluk sekmeyi açar
                            activeFocusOnTab: true
                            Accessible.role: Accessible.PageTab
                            Accessible.name: modelData.title
                            Accessible.selected: isActive
                            Accessible.onPressAction: window.currentTab = modelData.idx
                            Keys.onReturnPressed: window.currentTab = modelData.idx
                            Keys.onEnterPressed: window.currentTab = modelData.idx
                            Keys.onSpacePressed: window.currentTab = modelData.idx
                            FocusRing {}

                            // Seçili: içerikle aynı bej. Pasif: mavi gradyan (üzerine gelince açılır)
                            color: isActive ? AppTheme.tabActiveBg : "transparent"
                            gradient: isActive ? null : idleGradient
                            property Gradient idleGradient: Gradient {
                                GradientStop { position: 0.0; color: tabBtn.isHovered ? AppTheme.tabIdleHover : AppTheme.tabIdleTop }
                                GradientStop { position: 1.0; color: AppTheme.tabIdleBottom }
                            }

                            border.color: isActive ? AppTheme.border : AppTheme.tabIdleBorder
                            border.width: 1

                            // Seçili sekmenin alt kenarlığını kapatır (içeriğe kaynaşma)
                            Rectangle {
                                visible: tabBtn.isActive
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: 1
                                anchors.rightMargin: 1
                                height: 2
                                color: AppTheme.tabActiveBg
                            }

                            // XP seçili sekme üst vurgusu
                            Rectangle {
                                visible: tabBtn.isActive
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.leftMargin: 1
                                anchors.rightMargin: 1
                                anchors.topMargin: 1
                                height: 3
                                topLeftRadius: 4
                                topRightRadius: 4
                                color: AppTheme.tabActiveLine
                            }

                            RowLayout {
                                id: tabRow
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset: tabBtn.isActive ? 1 : 2
                                spacing: 8

                                // İç boşluk satırın kendi içinde: sekme genişliği düzey değişiminden bağımsız hesaplanır
                                Item { Layout.preferredWidth: window.iconOnlyTabs ? 0 : (window.compactHeader ? 2 : 4) }

                                SvgIcon {
                                    source: modelData.icon
                                    size: 16
                                    color: tabBtn.isActive ? AppTheme.accent : AppTheme.tabIdleText
                                }

                                Text {
                                    visible: tabBtn.isActive || !window.iconOnlyTabs
                                    text: modelData.title
                                    color: tabBtn.isActive ? AppTheme.tabActiveText : AppTheme.tabIdleText
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: true
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

                // Sağ: Proje Açma & Tema Değiştirme
                RowLayout {
                    id: headerRight
                    anchors.right: parent.right
                    anchors.rightMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12

                    // Proje Seçim Butonu: proje yokken yeşil "Başlat" düğmesi, varken bej düğme
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
                        tooltip: AppTheme.isDark ? "Açık temaya geç" : "Koyu temaya geç"
                        iconSource: AppTheme.isDark ? AppIcons.sun : AppIcons.moon
                        iconColor: AppTheme.titleText
                        color: isHovered ? Qt.rgba(1, 1, 1, 0.22) : "transparent"
                        border.color: isHovered ? Qt.rgba(1, 1, 1, 0.6) : "transparent"
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
