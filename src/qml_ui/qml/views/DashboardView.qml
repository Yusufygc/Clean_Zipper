import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "../singletons"
import "../components"

Item {
    id: root

    // HTML Rapor Kaydetme Diyaloğu
    FileDialog {
        id: saveHtmlDialog
        title: AppStrings.exportHtmlReport
        fileMode: FileDialog.SaveFile
        nameFilters: ["HTML Dosyaları (*.html)", "Tüm Dosyalar (*.*)"]
        defaultSuffix: "html"
        currentFile: (appVM.hasProject ? ("file:///" + appVM.projectPath + "/" + appVM.projectName + "_saglik_raporu.html") : "")
        onAccepted: {
            var ok = scanVM.exportHtmlReport(selectedFile.toString())
            if (ok) appVM.setStatus("HTML sağlık raporu başarıyla kaydedildi.")
        }
    }

    // Markdown Denetim Raporu Kaydetme Diyaloğu
    FileDialog {
        id: saveAuditDialog
        title: AppStrings.exportAuditReport
        fileMode: FileDialog.SaveFile
        nameFilters: ["Markdown Dosyaları (*.md)", "Tüm Dosyalar (*.*)"]
        defaultSuffix: "md"
        currentFile: (appVM.hasProject ? ("file:///" + appVM.projectPath + "/" + appVM.projectName + "_denetim_raporu.md") : "")
        onAccepted: {
            var ok = scanVM.exportAuditReport(selectedFile.toString())
            if (ok) appVM.setStatus("V2 Markdown denetim raporu başarıyla kaydedildi.")
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // ══════════════════════════════════════════════════════════
        // 1. ÜST ARAÇ ÇUBUĞU (ACTION BAR)
        // ══════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                spacing: 2
                Text {
                    text: AppStrings.tabDashboard
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeLarge
                    font.bold: true
                    renderType: Text.NativeRendering
                }
                Text {
                    text: appVM.hasProject 
                          ? ("Proje: " + appVM.projectName) 
                          : AppStrings.noProjectSelected
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }
            }

            Item { Layout.fillWidth: true } // Yay

            // Rapor Butonları
            CustomButton {
                text: "HTML Raporu"
                iconSource: AppIcons.document
                variant: "secondary"
                enabled: appVM.hasProject && !scanVM.isScanning
                onClicked: saveHtmlDialog.open()
            }

            CustomButton {
                text: "Denetim Raporu"
                iconSource: AppIcons.document
                variant: "secondary"
                enabled: appVM.hasProject && !scanVM.isScanning
                onClicked: saveAuditDialog.open()
            }

            // Yeniden Analiz Et Butonu
            CustomButton {
                text: AppStrings.reAnalyze
                iconSource: AppIcons.refresh
                variant: "accent"
                enabled: appVM.hasProject && !scanVM.isScanning
                onClicked: scanVM.startQuickScan()
            }
        }

        // ══════════════════════════════════════════════════════════
        // 2. ANALİZ İLERLEME ÇUBUĞU (PROGRESS BANNER)
        // ══════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            radius: AppTheme.radiusSmall
            color: AppTheme.surfaceHover
            border.color: AppTheme.border
            border.width: 1
            visible: scanVM.isScanning

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
                    text: scanVM.progressText
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    font.bold: true
                    Layout.preferredWidth: 220
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 6
                    radius: 3
                    color: AppTheme.isDark ? "#1E293B" : "#E2E8F0"

                    Rectangle {
                        width: parent.width * (scanVM.progressPercent / 100)
                        height: parent.height
                        radius: 3
                        color: AppTheme.accent

                        Behavior on width { NumberAnimation { duration: 150 } }
                    }
                }

                Text {
                    text: "%" + scanVM.progressPercent
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
        // 3. KAYDIRILABİLİR İÇERİK (SCROLLABLE DASHBOARD BODY)
        // ══════════════════════════════════════════════════════════
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: 16

                // SATIR 1: SAĞLIK GAUGE & METRİK KARTLARI
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    // Sol: Sağlık Göstergesi Kartı
                    CardFrame {
                        Layout.preferredWidth: 230
                        Layout.fillHeight: true
                        padding: 16

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 8

                            Text {
                                text: AppStrings.healthScore
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeBase
                                font.bold: true
                                Layout.alignment: Qt.AlignHCenter
                                renderType: Text.NativeRendering
                            }

                            HealthGauge {
                                score: scanVM.healthScore
                                status: scanVM.healthStatus
                                gaugeSize: 160
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }
                    }

                    // Sağ: 4'lü Metrik Kartı Grid'i
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: 12
                        columnSpacing: 12

                        MetricCard {
                            title: AppStrings.totalFiles
                            value: scanVM.totalFiles.toString()
                            iconSource: AppIcons.document
                            iconColor: AppTheme.accent
                            Layout.fillWidth: true
                        }

                        MetricCard {
                            title: AppStrings.projectSize
                            value: scanVM.totalSizeMb.toFixed(1) + " MB"
                            subtitle: scanVM.potentialSavingsMb > 0 
                                      ? (scanVM.potentialSavingsMb.toFixed(1) + " MB potansiyel tasarruf") 
                                      : ""
                            iconSource: AppIcons.archive
                            iconColor: AppTheme.primary
                            Layout.fillWidth: true
                        }

                        MetricCard {
                            title: AppStrings.totalFolders
                            value: scanVM.totalDirs.toString()
                            iconSource: AppIcons.folder
                            iconColor: AppTheme.info
                            Layout.fillWidth: true
                        }

                        MetricCard {
                            title: AppStrings.detectedIssues
                            value: scanVM.issuesCount.toString()
                            iconSource: AppIcons.alert
                            iconColor: scanVM.issuesCount > 0 ? AppTheme.warning : AppTheme.success
                            Layout.fillWidth: true
                        }
                    }
                }

                // SATIR 2: 11 KATEGORİ SAĞLIK DAĞILIMI & DOSYA TÜRLERİ
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    // Sol: 11 Kategori Sağlık Dağılımı
                    CardFrame {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 600
                        padding: 16

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 8

                            RowLayout {
                                spacing: 8
                                SvgIcon {
                                    source: AppIcons.shield
                                    size: 16
                                    color: AppTheme.accent
                                }
                                Text {
                                    text: "Kategori Bazlı Sağlık Puanları (11 Kategori)"
                                    color: AppTheme.textPrimary
                                    font.family: AppTheme.fontFamily
                                    font.pixelSize: AppTheme.fontSizeBase
                                    font.bold: true
                                    renderType: Text.NativeRendering
                                }
                            }

                            GridLayout {
                                columns: 2
                                rowSpacing: 4
                                columnSpacing: 20
                                Layout.fillWidth: true

                                property var catLabels: ({
                                    "security": "Güvenlik",
                                    "complexity": "Karmaşıklık",
                                    "duplicate": "Çift Kod",
                                    "size": "Dosya Boyutu",
                                    "structure": "Proje Yapısı",
                                    "dependency": "Bağımlılık",
                                    "deadcode": "Ölü Kod",
                                    "architecture": "Mimari",
                                    "reliability": "Güvenilirlik",
                                    "testing": "Test Sağlığı",
                                    "hygiene": "Proje Hijyeni"
                                })

                                Repeater {
                                    model: [
                                        "security", "complexity", "duplicate", "size",
                                        "structure", "dependency", "deadcode", "architecture",
                                        "reliability", "testing", "hygiene"
                                    ]

                                    CategoryBar {
                                        title: parent.catLabels[modelData] || modelData
                                        score: scanVM.categoryScores[modelData] !== undefined 
                                               ? scanVM.categoryScores[modelData] 
                                               : 100
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }

                    // Sağ: Dosya Türü Dağılımı
                    DistributionBar {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 400
                        Layout.fillHeight: true
                        title: AppStrings.fileDistribution
                        dataMap: scanVM.fileTypeDistribution
                    }
                }

                // SATIR 3: ÖNERİLER & BÜTÜNLÜK GÖSTERGELERİ
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    // Sol: Öncelikli Sistem Önerileri
                    RecommendationList {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 500
                        recommendations: scanVM.topRecommendations
                    }

                    // Sağ: Analiz Bütünlüğü & Kapsamı
                    IntegrityCard {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 500
                        failedAnalyzers: scanVM.failedAnalyzers
                        skippedFiles: scanVM.skippedFiles
                        ignoredGitignore: scanVM.ignoredByGitignore
                        gitignoreApplied: scanVM.gitignoreApplied
                    }
                }
            }
        }
    }
}
