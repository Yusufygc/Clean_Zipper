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
            // Uçlarda dur: içerik uçtan öteye sürüklenip bırakılınca geri sıçramasın
            Component.onCompleted: contentItem.boundsBehavior = Flickable.StopAtBounds

            ColumnLayout {
                width: parent.width
                spacing: 16

                // Düzen: her satır eşit genişlikli sütunlardır (Layout.preferredWidth: 1 + fillWidth) ve
                // aynı satırdaki kartlar en yüksek kartın boyuna uzar (Layout.fillHeight); böylece sayfa simetrik kalır.

                // SATIR 1: 4 metrik kartı (dar pencerede 2 x 2)
                GridLayout {
                    objectName: "metricGrid"
                    Layout.fillWidth: true
                    columns: root.width < 1100 ? 2 : 4
                    rowSpacing: 16
                    columnSpacing: 16

                    MetricCard {
                        title: AppStrings.totalFiles
                        value: scanVM.totalFiles.toString()
                        iconSource: AppIcons.document
                        iconColor: AppTheme.accent
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
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
                        Layout.preferredWidth: 1
                    }

                    MetricCard {
                        title: AppStrings.totalFolders
                        value: scanVM.totalDirs.toString()
                        iconSource: AppIcons.folder
                        iconColor: AppTheme.info
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                    }

                    MetricCard {
                        title: AppStrings.detectedIssues
                        value: scanVM.issuesCount.toString()
                        iconSource: AppIcons.alert
                        iconColor: scanVM.issuesCount > 0 ? AppTheme.warning : AppTheme.success
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                    }
                }

                // SATIR 2: sağlık skoru | kategori puanları
                RowLayout {
                    objectName: "healthRow"
                    Layout.fillWidth: true
                    spacing: 16

                    CardFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        padding: 16

                        ColumnLayout {
                            width: parent.width
                            height: parent.height
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

                            Item { Layout.fillHeight: true }

                            HealthGauge {
                                score: scanVM.healthScore
                                status: scanVM.healthStatus
                                gaugeSize: 260
                                Layout.alignment: Qt.AlignHCenter
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }

                    CardFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        padding: 16

                        ColumnLayout {
                            width: parent.width
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

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

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
                }

                // SATIR 3: dosya türü dağılımı | programlama dilleri dağılımı
                RowLayout {
                    objectName: "distributionRow"
                    Layout.fillWidth: true
                    spacing: 16

                    DistributionBar {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        title: AppStrings.fileDistribution
                        dataMap: scanVM.fileTypeDistribution
                    }

                    DistributionBar {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        title: AppStrings.languageDistribution + " (satır)"
                        dataMap: scanVM.languageLines
                    }
                }

                // SATIR 4: öncelikli öneriler | analiz bütünlüğü
                RowLayout {
                    objectName: "insightRow"
                    Layout.fillWidth: true
                    spacing: 16

                    RecommendationList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        recommendations: scanVM.topRecommendations
                    }

                    IntegrityCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        failedAnalyzers: scanVM.failedAnalyzers
                        skippedFiles: scanVM.skippedFiles
                        skippedDetail: scanVM.skippedDetail
                        ignoredGitignore: scanVM.ignoredByGitignore
                        gitignoreApplied: scanVM.gitignoreApplied
                    }
                }
            }
        }
    }
}
