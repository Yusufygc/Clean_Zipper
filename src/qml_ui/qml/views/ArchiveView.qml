import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "../singletons"
import "../components"

Item {
    id: root

    property int activeMode: 0 // 0: Zip, 1: Kopya, 2: Yedek

    // Zip Hedef Dosya Seçici
    FileDialog {
        id: zipSaveDialog
        title: "Arşiv Zip Konumu Seçin"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Zip Arşivleri (*.zip)", "Tüm Dosyalar (*.*)"]
        defaultSuffix: "zip"
        currentFile: (appVM.hasProject ? ("file:///" + appVM.projectPath + "/" + appVM.projectName + "_temiz_arsiv.zip") : "")
        onAccepted: {
            archiveVM.startZipArchive(selectedFile.toString())
        }
    }

    // Klasör Kopyası Hedef Dizin Seçici
    FolderDialog {
        id: copyFolderDialog
        title: "Temiz Kopya Çıkarılacak Hedef Klasörü Seçin"
        onAccepted: {
            archiveVM.startCleanCopy(selectedFolder.toString())
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // ══════════════════════════════════════════════════════════
        // 1. ÜST BAŞLIK & MOD SEÇİMİ
        // ══════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            ColumnLayout {
                spacing: 2
                Text {
                    text: AppStrings.archiveTitle
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeLarge
                    font.bold: true
                    renderType: Text.NativeRendering
                }
                Text {
                    text: AppStrings.archiveSubtitle
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }
            }

            Item { Layout.fillWidth: true }

            // Mod Seçici Haplar (Segmented Toggle)
            RowLayout {
                spacing: 4

                Repeater {
                    model: [
                        { idx: 0, label: "Zip Arşivi", icon: AppIcons.archive },
                        { idx: 1, label: "Temiz Kopya", icon: AppIcons.copy },
                        { idx: 2, label: "Proje Yedeği", icon: AppIcons.folder }
                    ]

                    Rectangle {
                        readonly property bool isCur: root.activeMode === modelData.idx
                        implicitWidth: modeRow.implicitWidth + 20
                        implicitHeight: 34
                        radius: AppTheme.radiusBase
                        color: isCur ? AppTheme.surfaceActive : (modeMouse.containsMouse ? AppTheme.surfaceHover : AppTheme.surface)
                        border.color: isCur ? AppTheme.accent : AppTheme.border
                        border.width: isCur ? 2 : 1

                        RowLayout {
                            id: modeRow
                            anchors.centerIn: parent
                            spacing: 6

                            SvgIcon {
                                source: modelData.icon
                                size: 14
                                color: isCur ? AppTheme.accent : AppTheme.textSecondary
                            }

                            Text {
                                text: modelData.label
                                color: isCur ? AppTheme.textPrimary : AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: isCur
                                renderType: Text.NativeRendering
                            }
                        }

                        MouseArea {
                            id: modeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeMode = modelData.idx
                        }
                    }
                }
            }
        }

        // ══════════════════════════════════════════════════════════
        // 2. İŞLEM İLERLEME ÇUBUĞU
        // ══════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            radius: AppTheme.radiusSmall
            color: AppTheme.surfaceHover
            border.color: AppTheme.border
            border.width: 1
            visible: archiveVM.isProcessing

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 12

                SvgIcon {
                    source: AppIcons.refresh
                    size: 16
                    color: AppTheme.accent
                }

                Text {
                    text: archiveVM.progressText
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    font.bold: true
                    Layout.preferredWidth: 260
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 6
                    radius: 3
                    color: AppTheme.isDark ? "#1E293B" : "#E2E8F0"

                    Rectangle {
                        width: parent.width * (archiveVM.progressPercent / 100)
                        height: parent.height
                        radius: 3
                        color: AppTheme.accent
                        Behavior on width { NumberAnimation { duration: 150 } }
                    }
                }

                Text {
                    text: "%" + archiveVM.progressPercent
                    color: AppTheme.accent
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    font.bold: true
                    Layout.preferredWidth: 36
                    horizontalAlignment: Text.AlignRight
                    renderType: Text.NativeRendering
                }
            }
        }

        // ══════════════════════════════════════════════════════════
        // 3. KAYDIRILABİLİR İÇERİK
        // ══════════════════════════════════════════════════════════
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            // Uçlarda dur: içerik uçtan öteye sürüklenip bırakılınca geri sıçramasın
            Component.onCompleted: contentItem.boundsBehavior = Flickable.StopAtBounds
            // İçerik yüksekliği düzenin gerçek yüksekliğidir; aksi hâlde son satır kesik kalır (kaydırma ucu erken biter)
            contentHeight: bodyColumn.implicitHeight

            ColumnLayout {
                id: bodyColumn
                width: parent.width
                spacing: 16

                // ── MOD 0 & 1: PROFİL SEÇİMİ VE ARŞİV/KOPYA EYLEMİ ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    visible: root.activeMode === 0 || root.activeMode === 1

                    // Profil Seçim Kartı
                    CardFrame {
                        Layout.fillWidth: true
                        padding: 16

                        ColumnLayout {
                            width: parent.width
                            spacing: 12

                            RowLayout {
                                spacing: 8
                                SvgIcon {
                                    source: AppIcons.settings
                                    size: 16
                                    color: AppTheme.accent
                                }
                                Text {
                                    text: "Sıkıştırma & Temizleme Profili"
                                    color: AppTheme.textPrimary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: true
                                    renderType: Text.NativeRendering
                                }
                            }

                            // Profil Kartları
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                Repeater {
                                    model: archiveVM.profiles

                                    Rectangle {
                                        readonly property bool isSel: archiveVM.selectedProfile === modelData.name
                                        Layout.fillWidth: true
                                        implicitHeight: profCol.implicitHeight + 20
                                        radius: AppTheme.radiusBase
                                        color: isSel ? AppTheme.surfaceActive : (profMouse.containsMouse ? AppTheme.surfaceHover : AppTheme.surface)
                                        border.color: isSel ? AppTheme.accent : AppTheme.border
                                        border.width: isSel ? 2 : 1

                                        ColumnLayout {
                                            id: profCol
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 6

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text {
                                                    text: modelData.name
                                                    color: isSel ? AppTheme.accent : AppTheme.textPrimary
                                                    font.family: AppTheme.fontFamily
                                                    font.pixelSize: AppTheme.fontSizeBase
                                                    font.bold: true
                                                    renderType: Text.NativeRendering
                                                }
                                                Item { Layout.fillWidth: true }
                                                SvgIcon {
                                                    source: AppIcons.check
                                                    size: 16
                                                    color: AppTheme.accent
                                                    visible: isSel
                                                }
                                            }

                                            Text {
                                                text: modelData.description
                                                color: AppTheme.textSecondary
                                                font.family: AppTheme.fontFamily
                                                font.pixelSize: 12
                                                wrapMode: Text.WordWrap
                                                Layout.fillWidth: true
                                                renderType: Text.NativeRendering
                                            }
                                        }

                                        MouseArea {
                                            id: profMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: archiveVM.selectProfile(modelData.name)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Eylem Kartı
                    CardFrame {
                        Layout.fillWidth: true
                        padding: 16

                        RowLayout {
                            anchors.fill: parent
                            spacing: 16

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.maximumWidth: 100000
                                spacing: 4

                                Text {
                                    text: root.activeMode === 0 
                                          ? "Zip Arşivi Hazırla" 
                                          : "Temiz Klasör Kopyası Oluştur"
                                    color: AppTheme.textPrimary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: true
                                    renderType: Text.NativeRendering
                                }
                                Text {
                                    text: root.activeMode === 0
                                          ? "Seçilen profile göre gereksiz dosyaları ve dışlanan klasörleri eleyerek .zip paketi üretir."
                                          : "Projenizi belirlenen hedef klasöre temizlenmiş ve dağıtıma hazır halde kopyalar."
                                    color: AppTheme.textSecondary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeSmall
                                    renderType: Text.NativeRendering
                                }
                            }

                            CustomButton {
                                text: root.activeMode === 0 ? "Zip Konumu Seç ve Arşivle" : "Hedef Klasör Seç ve Kopyala"
                                iconSource: root.activeMode === 0 ? AppIcons.archive : AppIcons.copy
                                variant: "accent"
                                enabled: appVM.hasProject && !archiveVM.isProcessing
                                onClicked: {
                                    if (root.activeMode === 0) zipSaveDialog.open()
                                    else copyFolderDialog.open()
                                }
                            }
                        }
                    }
                }

                // ── MOD 2: YEDEKLEME MODU ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    visible: root.activeMode === 2

                    // Yedek Alma Kartı
                    CardFrame {
                        Layout.fillWidth: true
                        padding: 16

                        RowLayout {
                            anchors.fill: parent
                            spacing: 16

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.maximumWidth: 100000
                                spacing: 4

                                Text {
                                    text: AppStrings.takeBackup
                                    color: AppTheme.textPrimary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: true
                                    renderType: Text.NativeRendering
                                }
                                Text {
                                    text: AppStrings.backupDescription
                                    color: AppTheme.textSecondary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeSmall
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                    renderType: Text.NativeRendering
                                }

                                // Proje başına saklanan otomatik yedek (eskiler Geri Dönüşüm Kutusu'na; 0 = sınırsız)
                                RowLayout {
                                    objectName: "maxBackupsRow"
                                    spacing: 4
                                    Text {
                                        text: AppStrings.keptBackups
                                        color: AppTheme.textSecondary
                                        font.family: AppTheme.fontFamily
                                        font.pixelSize: AppTheme.fontSizeSmall
                                        renderType: Text.NativeRendering
                                    }
                                    CustomButton {
                                        text: "-"
                                        variant: "secondary"
                                        Layout.preferredWidth: 36
                                        onClicked: settingsVM.adjustMaxBackups(-1)
                                    }
                                    Text {
                                        text: settingsVM.maxBackups === 0 ? "∞" : settingsVM.maxBackups.toString()
                                        color: AppTheme.accent
                                        font.family: AppTheme.fontFamily
                                        font.bold: true
                                        Layout.preferredWidth: 32
                                        horizontalAlignment: Text.AlignHCenter
                                        renderType: Text.NativeRendering
                                    }
                                    CustomButton {
                                        text: "+"
                                        variant: "secondary"
                                        Layout.preferredWidth: 36
                                        onClicked: settingsVM.adjustMaxBackups(1)
                                    }
                                }
                            }

                            CustomButton {
                                text: "Hızlı Yedek Al"
                                iconSource: AppIcons.folder
                                variant: "primary"
                                enabled: appVM.hasProject && !archiveVM.isProcessing
                                onClicked: archiveVM.startBackup()
                            }
                        }
                    }

                    // Mevcut Yedekler Listesi
                    CardFrame {
                        Layout.fillWidth: true
                        padding: 16

                        ColumnLayout {
                            width: parent.width
                            spacing: 12

                            RowLayout {
                                spacing: 8
                                SvgIcon {
                                    source: AppIcons.archive
                                    size: 16
                                    color: AppTheme.accent
                                }
                                Text {
                                    text: "Mevcut Yedekler (~/.gitclean_backups)"
                                    color: AppTheme.textPrimary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: true
                                    renderType: Text.NativeRendering
                                }
                            }

                            Text {
                                text: "Henüz oluşturulmuş bir yedek bulunmuyor."
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                visible: archiveVM.backupList.length === 0
                                renderType: Text.NativeRendering
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                visible: archiveVM.backupList.length > 0

                                Repeater {
                                    model: archiveVM.backupList

                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 40
                                        radius: AppTheme.radiusSmall
                                        color: AppTheme.surfaceHover
                                        border.color: AppTheme.border
                                        border.width: 1

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 12

                                            SvgIcon {
                                                source: AppIcons.archive
                                                size: 16
                                                color: AppTheme.textSecondary
                                            }

                                            Text {
                                                text: modelData.name
                                                color: AppTheme.textPrimary
                                                font.family: AppTheme.fontFamily
                                                font.pixelSize: AppTheme.fontSizeSmall
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                                renderType: Text.NativeRendering
                                            }

                                            Badge {
                                                text: modelData.sizeMb + " MB"
                                                textColor: AppTheme.accent
                                                badgeColor: AppTheme.surfaceActive
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── İŞLEM SONUCU KARTI (ORTAK) ──
                CardFrame {
                    Layout.fillWidth: true
                    padding: 16
                    visible: archiveVM.hasResult

                    ColumnLayout {
                        width: parent.width
                        spacing: 12

                        // Durum Başlığı
                        RowLayout {
                            spacing: 8

                            SvgIcon {
                                source: archiveVM.lastResult.success ? AppIcons.check : AppIcons.alert
                                size: 20
                                color: archiveVM.lastResult.success ? AppTheme.success : AppTheme.danger
                            }

                            Text {
                                text: archiveVM.lastResult.error
                                      ? "İşlem Reddedildi / Hata"
                                      : (archiveVM.lastResult.complete ? "İşlem Eksiksiz Tamamlandı" : "Kısmi Tamamlandı (Bazı Dosyalar Eklenemedi)")
                                color: archiveVM.lastResult.error ? AppTheme.danger : (archiveVM.lastResult.complete ? AppTheme.success : AppTheme.warning)
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeBase
                                font.bold: true
                                renderType: Text.NativeRendering
                            }
                        }

                        // Hata Mesajı veya Gitignore Güvenlik Durdurması
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: errText.implicitHeight + 16
                            radius: AppTheme.radiusSmall
                            color: AppTheme.dangerBg
                            border.color: AppTheme.danger
                            border.width: 1
                            visible: archiveVM.lastResult.error !== ""

                            Text {
                                id: errText
                                anchors.fill: parent
                                anchors.margins: 10
                                text: archiveVM.lastResult.error
                                color: AppTheme.danger
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                wrapMode: Text.WordWrap
                                renderType: Text.NativeRendering
                            }
                        }

                        // Metrikler
                        GridLayout {
                            columns: 3
                            rowSpacing: 8
                            columnSpacing: 16
                            Layout.fillWidth: true
                            visible: !archiveVM.lastResult.error

                            Text {
                                text: archiveVM.lastResult.mode === "backup" ? "Yedek Boyutu:" : "İşlenen / Eklenen Dosya:"
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                            }
                            Badge {
                                text: archiveVM.lastResult.mode === "backup"
                                      ? (archiveVM.lastResult.backupSizeMb + " MB")
                                      : (archiveVM.lastResult.addedFiles + " dosya")
                                textColor: AppTheme.success
                                badgeColor: AppTheme.surfaceActive
                            }
                            Item { Layout.fillWidth: true }

                            Text {
                                text: archiveVM.lastResult.mode === "backup" ? "Dışlanan Klasör (yeniden üretilebilir):" : "Atlanan Dosya (Filtre Dışı):"
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                            }
                            Badge {
                                text: archiveVM.lastResult.mode === "backup"
                                      ? (archiveVM.lastResult.excludedDirsCount + " klasör")
                                      : (archiveVM.lastResult.skippedFiles + " dosya")
                                textColor: AppTheme.textSecondary
                                badgeColor: AppTheme.surfaceActive
                            }
                            Item { Layout.fillWidth: true }

                            Text {
                                text: "Çıktı Konumu:"
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                            }
                            Text {
                                text: archiveVM.lastResult.outputPath
                                color: AppTheme.accent
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                elide: Text.ElideMiddle
                                Layout.maximumWidth: 400
                                renderType: Text.NativeRendering
                            }
                            Item { Layout.fillWidth: true }
                        }

                        // Eklenemeyen Hatalı Dosyalar Listesi (Varsa)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: archiveVM.lastResult.failedFilesCount > 0

                            Text {
                                text: "Eklenemeyen Dosyalar (" + archiveVM.lastResult.failedFilesCount + "):"
                                color: AppTheme.danger
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                            }

                            Repeater {
                                model: archiveVM.lastResult.failedFiles

                                Text {
                                    text: "- " + modelData
                                    color: AppTheme.textSecondary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: 12
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
}
