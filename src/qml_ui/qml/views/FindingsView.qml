import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../singletons"
import "../components"

Item {
    id: root

    readonly property bool filtersActive: findingsVM.selectedSeverity !== "ALL" || findingsVM.selectedCategory !== "ALL"
                                          || searchInput.text !== ""

    function clearFilters() {
        searchInput.text = ""
        findingsVM.setSeverityFilter("ALL")
        findingsVM.setCategoryFilter("ALL")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // ══════════════════════════════════════════════════════════
        // 1. ÜST ARAÇ ÇUBUĞU (ACTION BAR & SEARCH)
        // ══════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                spacing: 2
                Text {
                    text: AppStrings.tabFindings
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeLarge
                    font.bold: true
                    renderType: Text.NativeRendering
                }
                Text {
                    text: "Toplam " + findingsVM.totalCount + " adet bulgu ve yapısal kural tespiti"
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }
            }

            Item { Layout.fillWidth: true } // Yay

            // Arama Kutusu
            Rectangle {
                Layout.preferredWidth: 260
                Layout.preferredHeight: 36
                radius: AppTheme.radiusBase
                color: AppTheme.surface
                border.color: searchInput.activeFocus ? AppTheme.accent : AppTheme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    SvgIcon {
                        source: AppIcons.search
                        size: 16
                        color: searchInput.activeFocus ? AppTheme.accent : AppTheme.textMuted
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        selectByMouse: true
                        renderType: Text.NativeRendering

                        Text {
                            text: "Bulgu, kural veya dosya ara..."
                            color: AppTheme.textMuted
                            font.family: AppTheme.fontFamily
                            font.pixelSize: AppTheme.fontSizeSmall
                            visible: !searchInput.text && !searchInput.activeFocus
                            renderType: Text.NativeRendering
                        }

                        onTextChanged: findingsVM.setSearchQuery(text)
                    }

                    IconButton {
                        iconSource: AppIcons.cross
                        iconSize: 12
                        visible: searchInput.text !== ""
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                        onClicked: {
                            searchInput.text = ""
                            findingsVM.setSearchQuery("")
                        }
                    }
                }
            }

            // Derin Teşhis Çalıştır Butonu
            CustomButton {
                text: "Derin Teşhis Yenile"
                iconSource: AppIcons.refresh
                variant: "accent"
                enabled: appVM.hasProject && !findingsVM.isDiagnosing
                onClicked: findingsVM.startDeepDiagnosis()
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
            visible: findingsVM.isDiagnosing

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
                    text: findingsVM.progressText
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    font.bold: true
                    Layout.preferredWidth: 240
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 6
                    radius: 3
                    color: AppTheme.trackBg

                    Rectangle {
                        width: parent.width * (findingsVM.progressPercent / 100)
                        height: parent.height
                        radius: 3
                        color: AppTheme.accent
                        Behavior on width { NumberAnimation { duration: 150 } }
                    }
                }

                Text {
                    text: "%" + findingsVM.progressPercent
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
        // 3. SÜZGEÇ ÇUBUĞU: şiddet (bitişik seçenekler) + kategori (açılır liste) + sonuç sayısı
        // ══════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            SegmentedFilter {
                objectName: "severityFilter"
                current: findingsVM.selectedSeverity
                options: [
                    { key: "ALL", label: "Tümü", count: findingsVM.totalCount, color: AppTheme.accent },
                    { key: "CRITICAL", label: "Kritik", count: findingsVM.criticalCount, color: AppTheme.danger },
                    { key: "HIGH", label: "Yüksek", count: findingsVM.highCount, color: "#EA580C" },
                    { key: "MEDIUM", label: "Orta", count: findingsVM.mediumCount, color: AppTheme.warning },
                    { key: "LOW", label: "Düşük", count: findingsVM.lowCount, color: AppTheme.primary },
                    { key: "INFO", label: "Bilgi", count: findingsVM.infoCount, color: AppTheme.success }
                ]
                onSelected: function(key) { findingsVM.setSeverityFilter(key) }
            }

            FilterComboBox {
                objectName: "categoryFilter"
                caption: "Kategori:"
                current: findingsVM.selectedCategory
                enabled: findingsVM.categories.length > 0
                model: {
                    var items = [{ key: "ALL", label: "Tümü", count: findingsVM.totalCount }]
                    for (var i = 0; i < findingsVM.categories.length; i++) {
                        var c = findingsVM.categories[i]
                        items.push({ key: c.key, label: c.name, count: c.count })
                    }
                    return items
                }
                onPicked: function(key) { findingsVM.setCategoryFilter(key) }
            }

            Item { Layout.fillWidth: true }

            Text {
                objectName: "resultCount"
                text: findingsList.count + " sonuç"
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                renderType: Text.NativeRendering
            }

            CustomButton {
                objectName: "clearFilters"
                text: "Süzgeçleri Temizle"
                variant: "secondary"
                visible: root.filtersActive
                onClicked: root.clearFilters()
            }
        }

        // ══════════════════════════════════════════════════════════
        // 4. BULGULAR LİSTESİ (FINDINGS LISTVIEW)
        // ══════════════════════════════════════════════════════════
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Boş Durum (Empty State)
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                visible: findingsList.count === 0 && !findingsVM.isDiagnosing

                SvgIcon {
                    source: AppIcons.check
                    size: 48
                    color: AppTheme.success
                    Layout.alignment: Qt.AlignHCenter
                }

                Text {
                    text: appVM.hasProject 
                          ? AppStrings.noIssuesFound 
                          : AppStrings.selectProjectPrompt
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeMedium
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                    renderType: Text.NativeRendering
                }

                Text {
                    text: appVM.hasProject 
                          ? "Filtre kriterlerinizi değiştirebilir veya derin teşhisi yenileyebilirsiniz." 
                          : "Bulguları listelemek için lütfen bir proje dizini açın."
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    Layout.alignment: Qt.AlignHCenter
                    renderType: Text.NativeRendering
                }
            }

            // Liste
            ListView {
                id: findingsList
                boundsBehavior: Flickable.StopAtBounds
                anchors.fill: parent
                clip: true
                spacing: 10
                model: findingsVM.model
                visible: findingsList.count > 0

                delegate: FindingCard {
                    width: findingsList.width - AppTheme.scrollGutter
                    title: model.title
                    description: model.description
                    severity: model.severity
                    categoryName: model.categoryName
                    fileName: model.fileName
                    filePath: model.filePath
                    relPath: model.relPath
                    line: model.line
                    suggestion: model.suggestion
                    rule: model.rule
                    ruleLabel: model.ruleLabel
                    effort: model.effort
                    isSecret: model.isSecret
                    approximate: model.approximate
                    onDisableRuleRequested: function(ruleId) { settingsVM.disableRule(ruleId) }
                }

                ScrollBar.vertical: ThemedScrollBar { active: true }
            }
        }
    }
}
