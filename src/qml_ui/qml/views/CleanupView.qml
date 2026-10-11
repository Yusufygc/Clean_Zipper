import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../singletons"
import "../components"

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // ══════════════════════════════════════════════════════════
        // 1. ÜST BAŞLIK & AÇIKLAMA
        // ══════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            ColumnLayout {
                spacing: 2
                Text {
                    text: AppStrings.cleanupTitle
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeLarge
                    font.bold: true
                    renderType: Text.NativeRendering
                }
                Text {
                    text: AppStrings.cleanupSubtitle
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }
            }

            Item { Layout.fillWidth: true }

            // Butonlar
            CustomButton {
                text: "Önizleme (Tara)"
                iconSource: AppIcons.search
                variant: "secondary"
                enabled: appVM.hasProject && !cleanupVM.isProcessing
                onClicked: cleanupVM.startPreview()
            }

            CustomButton {
                text: "Temizliği Başlat"
                iconSource: AppIcons.trash
                variant: "danger"
                enabled: appVM.hasProject && !cleanupVM.isProcessing
                onClicked: cleanupVM.startCleanup()
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
            visible: cleanupVM.isProcessing

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
                    text: cleanupVM.progressText
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
                    color: AppTheme.trackBg

                    Rectangle {
                        width: parent.width * (cleanupVM.progressPercent / 100)
                        height: parent.height
                        radius: 3
                        color: AppTheme.danger
                        Behavior on width { NumberAnimation { duration: 150 } }
                    }
                }

                Text {
                    text: "%" + cleanupVM.progressPercent
                    color: AppTheme.danger
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
        // 3. KATEGORİ SEÇİM KARTI
        // ══════════════════════════════════════════════════════════
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
                        text: "Temizlik Kategorileri"
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeBase
                        font.bold: true
                        renderType: Text.NativeRendering
                    }
                }

                GridLayout {
                    columns: 2
                    rowSpacing: 10
                    columnSpacing: 24
                    Layout.fillWidth: true

                    // 1. Python Önbelleği
                    RowLayout {
                        spacing: 10
                        AppCheckBox {
                            accessibleName: "Python önbelleği"
                            checked: cleanupVM.categoryPythonCache
                            onToggled: cleanupVM.setCategory("python_cache", checked)
                        }
                        ColumnLayout {
                            spacing: 1
                            Text {
                                text: "Python Önbelleği (__pycache__, *.pyc, *.pyo)"
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                renderType: Text.NativeRendering
                            }
                            Text {
                                text: "Derlenmiş Python baytkod dosyalarını ve önbellek klasörlerini temizler."
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: 12
                                renderType: Text.NativeRendering
                            }
                        }
                    }

                    // 2. Geçici Dosyalar
                    RowLayout {
                        spacing: 10
                        AppCheckBox {
                            accessibleName: "Geçici dosyalar"
                            checked: cleanupVM.categoryTempFiles
                            onToggled: cleanupVM.setCategory("temp_files", checked)
                        }
                        ColumnLayout {
                            spacing: 1
                            Text {
                                text: "Geçici Dosyalar (*.tmp)"
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                renderType: Text.NativeRendering
                            }
                            Text {
                                text: "Editörlerin veya araçların bıraktığı artık geçici dosyaları temizler."
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: 12
                                renderType: Text.NativeRendering
                            }
                        }
                    }

                    // 3. Log Dosyaları
                    RowLayout {
                        spacing: 10
                        AppCheckBox {
                            accessibleName: "Log dosyaları"
                            checked: cleanupVM.categoryLogs
                            onToggled: cleanupVM.setCategory("logs", checked)
                        }
                        ColumnLayout {
                            spacing: 1
                            Text {
                                text: "Log Dosyaları (*.log)"
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                renderType: Text.NativeRendering
                            }
                            Text {
                                text: "Çalışma zamanı günlük dosyaları (kullanıcı verisi içerebilir)."
                                color: AppTheme.warning
                                font.family: AppTheme.fontFamily
                                font.pixelSize: 12
                                renderType: Text.NativeRendering
                            }
                        }
                    }

                    // 4. Yedek Dosyaları
                    RowLayout {
                        spacing: 10
                        AppCheckBox {
                            accessibleName: "Yedek dosyaları"
                            checked: cleanupVM.categoryBackups
                            onToggled: cleanupVM.setCategory("backups", checked)
                        }
                        ColumnLayout {
                            spacing: 1
                            Text {
                                text: "Yedek Dosyaları (*.bak)"
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                renderType: Text.NativeRendering
                            }
                            Text {
                                text: "Eski yedek kalıntıları (kullanıcı verisi içerebilir)."
                                color: AppTheme.warning
                                font.family: AppTheme.fontFamily
                                font.pixelSize: 12
                                renderType: Text.NativeRendering
                            }
                        }
                    }
                }
            }
        }

        // ══════════════════════════════════════════════════════════
        // 4. GÜVENLİK VE GERİ DÖNÜŞÜM BİLDİRİMİ
        // ══════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 38
            radius: AppTheme.radiusSmall
            color: AppTheme.codeBg
            border.color: AppTheme.border
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                SvgIcon {
                    source: AppIcons.shield
                    size: 16
                    color: AppTheme.accent
                }

                Text {
                    text: AppStrings.cleanupNotice
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: 12
                    font.bold: true
                    renderType: Text.NativeRendering
                }
            }
        }

        // ══════════════════════════════════════════════════════════
        // 5. ÖNİZLEME VEYA TEMİZLİK SONUCU LİSTESİ
        // ══════════════════════════════════════════════════════════
        CardFrame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            padding: 16

            ColumnLayout {
                // Yükseklik kartın iç alanı kadar: aksi hâlde liste ve boş durum 0 px yükseklikte kalır (görünmez)
                width: parent.width
                height: parent.height
                spacing: 12

                // Başlık & Özet Rozetler
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: cleanupVM.lastResult.cleanedFiles !== undefined 
                              ? "Son Temizlik Sonucu" 
                              : "Önizleme Listesi"
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeBase
                        font.bold: true
                        renderType: Text.NativeRendering
                    }

                    Item { Layout.fillWidth: true }

                    // Önizleme Bilgi Rozetleri
                    Badge {
                        text: cleanupVM.previewCount + " öğe tespit edildi"
                        textColor: AppTheme.accent
                        badgeColor: AppTheme.surfaceActive
                        visible: cleanupVM.previewCount > 0
                    }

                    Badge {
                        text: cleanupVM.previewSizeMb + " MB kazanılabilir"
                        textColor: AppTheme.success
                        badgeColor: AppTheme.surfaceActive
                        visible: cleanupVM.previewSizeMb > 0
                    }

                    // Temizlik Sonucu Rozeti
                    Badge {
                        text: cleanupVM.lastResult.cleanedFiles + " dosya taşındı (" + cleanupVM.lastResult.cleanedSizeMb + " MB)"
                        textColor: "#FFFFFF"
                        badgeColor: AppTheme.success
                        visible: cleanupVM.lastResult.cleanedFiles !== undefined
                    }
                }

                // Boş Durum
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: cleanupVM.previewFiles.length === 0 && cleanupVM.lastResult.cleanedFiles === undefined

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 10

                        SvgIcon {
                            source: AppIcons.trash
                            size: 40
                            color: AppTheme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: appVM.hasProject 
                                  ? "Önizleme yapmak için 'Önizleme (Tara)' butonuna tıklayın." 
                                  : AppStrings.selectProjectPrompt
                            color: AppTheme.textSecondary
                            font.family: AppTheme.fontFamily
                            font.pixelSize: AppTheme.fontSizeSmall
                            Layout.alignment: Qt.AlignHCenter
                            renderType: Text.NativeRendering
                        }
                    }
                }

                // Önizleme Dosya Listesi
                ListView {
                    id: cleanListView
                    objectName: "cleanList"
                    boundsBehavior: Flickable.StopAtBounds
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 6
                    model: cleanupVM.previewFiles
                    visible: cleanupVM.previewFiles.length > 0

                    delegate: Rectangle {
                        width: cleanListView.width - AppTheme.scrollGutter
                        implicitHeight: 36
                        radius: AppTheme.radiusSmall
                        color: AppTheme.surfaceHover
                        border.color: AppTheme.border
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 10

                            SvgIcon {
                                source: modelData.isDir ? AppIcons.folder : AppIcons.document
                                size: 14
                                color: AppTheme.textSecondary
                            }

                            Text {
                                text: modelData.name
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                elide: Text.ElideMiddle
                                Layout.preferredWidth: 200
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: modelData.path
                                color: AppTheme.textMuted
                                font.family: AppTheme.fontFamily
                                font.pixelSize: 12
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                                renderType: Text.NativeRendering
                            }

                            Badge {
                                text: modelData.categoryName
                                textColor: AppTheme.accent
                                badgeColor: AppTheme.surfaceActive
                                fontSize: 12
                            }

                            Badge {
                                text: modelData.sizeKb < 1 ? "< 1 KB" : modelData.sizeKb + " KB"
                                textColor: AppTheme.textSecondary
                                badgeColor: AppTheme.surfaceActive
                                fontSize: 12
                            }
                        }
                    }

                    ScrollBar.vertical: ThemedScrollBar { active: true }
                }
            }
        }
    }
}
