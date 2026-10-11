import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "../singletons"
import "../components"

Item {
    id: root

    property string bannerMessage: ""
    property bool bannerIsError: false
    property bool bannerVisible: false

    readonly property var agentResult: settingsVM.lastAgentResult
    readonly property string agentKind: agentResult.kind || ""

    function showBanner(message, isError) {
        root.bannerMessage = message
        root.bannerIsError = isError
        root.bannerVisible = true
    }

    FolderDialog {
        id: agentTaskFolderDialog
        title: "Ajan Görev Paketinin Kaydedileceği Dizini Seçin"
        onAccepted: settingsVM.setAgentOutputDir(selectedFolder.toString())
    }

    Connections {
        target: settingsVM
        function onSettingsApplied(message) { root.showBanner(message, message.indexOf("uygulanamadı") >= 0) }
        function onTaskExportError(errMsg) { root.showBanner("Hata: " + errMsg, true) }
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: 20
        contentWidth: availableWidth
        clip: true
        rightPadding: AppTheme.scrollGutter
        ScrollBar.vertical: ThemedScrollBar { }
        // Uçlarda dur: içerik uçtan öteye sürüklenip bırakılınca geri sıçramasın
        Component.onCompleted: contentItem.boundsBehavior = Flickable.StopAtBounds
        // İçerik yüksekliği düzenin gerçek yüksekliğidir; aksi hâlde son satır kesik kalır (kaydırma ucu erken biter)
        contentHeight: bodyColumn.implicitHeight

        ColumnLayout {
            id: bodyColumn
            width: parent.width
            spacing: 16

            // ── 1. Başlık ──
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: AppStrings.tabSettings
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeLarge
                        font.bold: true
                        renderType: Text.NativeRendering
                    }
                    Text {
                        text: AppStrings.thresholdSettingsDesc
                        color: AppTheme.textSecondary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        renderType: Text.NativeRendering
                    }
                }

                Item { Layout.fillWidth: true }

                CustomButton {
                    text: AppStrings.resetDefaultsBtn
                    variant: "secondary"
                    onClicked: settingsVM.resetToDefaults()
                }

                CustomButton {
                    text: AppStrings.applySettingsBtn
                    variant: "accent"
                    onClicked: settingsVM.applySettings()
                }
            }

            // ── Bildirim çubuğu ──
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                radius: AppTheme.radiusSmall
                visible: root.bannerVisible
                color: root.bannerIsError ? AppTheme.dangerBg : AppTheme.successBg
                border.color: root.bannerIsError ? AppTheme.danger : AppTheme.success
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    SvgIcon {
                        source: root.bannerIsError ? AppIcons.alert : AppIcons.check
                        size: 16
                        color: root.bannerIsError ? AppTheme.danger : AppTheme.success
                    }

                    Text {
                        text: root.bannerMessage
                        color: root.bannerIsError ? AppTheme.danger : AppTheme.success
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        renderType: Text.NativeRendering
                    }
                }
            }

            // ── 2. .gitignore ──
            CardFrame {
                Layout.fillWidth: true

                RowLayout {
                    width: parent.width
                    spacing: 12

                    AppCheckBox {
                        accessibleName: ".gitignore kurallarını uygula"
                        checked: settingsVM.respectGitignore
                        onToggled: settingsVM.setRespectGitignore(checked)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: AppStrings.respectGitignore
                            color: AppTheme.textPrimary
                            font.family: AppTheme.fontFamily
                            font.pixelSize: AppTheme.fontSizeBase
                            font.bold: true
                            renderType: Text.NativeRendering
                        }
                        Text {
                            text: AppStrings.respectGitignoreDesc + " Git'in izlediği dosyalar her zaman dahil edilir."
                            color: AppTheme.textSecondary
                            font.family: AppTheme.fontFamily
                            font.pixelSize: AppTheme.fontSizeSmall
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            renderType: Text.NativeRendering
                        }
                    }
                }
            }

            // ── 3. Eşikler (V2 tablosu, 9 değer) ──
            CardFrame {
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 12

                    Text {
                        text: AppStrings.thresholdSettings
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeBase
                        font.bold: true
                        renderType: Text.NativeRendering
                    }

                    GridLayout {
                        columns: 2
                        rowSpacing: 10
                        columnSpacing: 24
                        Layout.fillWidth: true

                        Repeater {
                            model: settingsVM.thresholds

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                // Etiket sabit genişlikte: eksi / artı düğmeleri etiketin hemen yanında durur
                                ColumnLayout {
                                    objectName: "thresholdLabel"
                                    Layout.preferredWidth: 190
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 0

                                    Text {
                                        text: modelData.label
                                        color: AppTheme.textPrimary
                                        font.family: AppTheme.fontFamily
                                        font.pixelSize: AppTheme.fontSizeSmall
                                        renderType: Text.NativeRendering
                                    }
                                    Text {
                                        text: "varsayılan " + modelData.default
                                        color: AppTheme.textMuted
                                        font.family: AppTheme.fontFamily
                                        font.pixelSize: 12
                                        visible: modelData.value !== modelData.default
                                        renderType: Text.NativeRendering
                                    }
                                }

                                CustomButton {
                                    objectName: "thresholdMinus"
                                    text: "-"
                                    variant: "secondary"
                                    Layout.preferredWidth: 36
                                    onClicked: settingsVM.adjustThreshold(modelData.key, -modelData.step)
                                }
                                Text {
                                    text: modelData.value.toString()
                                    color: modelData.value !== modelData.default ? AppTheme.warning : AppTheme.accent
                                    font.family: AppTheme.fontFamily
                                    font.bold: true
                                    Layout.preferredWidth: 44
                                    horizontalAlignment: Text.AlignHCenter
                                    renderType: Text.NativeRendering
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "secondary"
                                    Layout.preferredWidth: 36
                                    onClicked: settingsVM.adjustThreshold(modelData.key, modelData.step)
                                }

                                Item { Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            // ── 4. Analizörler ──
            CardFrame {
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.maximumWidth: 100000
                            spacing: 2
                            Text {
                                text: AppStrings.activeAnalyzers
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeBase
                                font.bold: true
                                renderType: Text.NativeRendering
                            }
                            Text {
                                text: AppStrings.activeAnalyzersDesc
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                renderType: Text.NativeRendering
                            }
                        }

                        CustomButton {
                            text: "Tümünü Aç"
                            variant: "secondary"
                            onClicked: settingsVM.enableAllAnalyzers()
                        }
                        CustomButton {
                            text: "Tümünü Kapat"
                            variant: "secondary"
                            onClicked: settingsVM.disableAllAnalyzers()
                        }
                    }

                    GridLayout {
                        columns: 2
                        rowSpacing: 12
                        columnSpacing: 16
                        Layout.fillWidth: true

                        Repeater {
                            model: settingsVM.analyzersList

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 64
                                radius: AppTheme.radiusSmall
                                color: modelData.enabled ? AppTheme.surfaceHover : AppTheme.surface
                                border.color: modelData.enabled ? AppTheme.border : AppTheme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 10

                                    AppCheckBox {
                                        accessibleName: modelData.name
                                        checked: modelData.enabled
                                        onToggled: settingsVM.toggleAnalyzer(modelData.id, checked)
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            text: modelData.name
                                            color: modelData.enabled ? AppTheme.textPrimary : AppTheme.textMuted
                                            font.family: AppTheme.fontFamily
                                            font.pixelSize: AppTheme.fontSizeSmall
                                            font.bold: true
                                            renderType: Text.NativeRendering
                                        }

                                        Text {
                                            text: modelData.description
                                            color: AppTheme.textSecondary
                                            font.family: AppTheme.fontFamily
                                            font.pixelSize: 12
                                            elide: Text.ElideRight
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

            // ── 5. Kapatılan kurallar ──
            CardFrame {
                Layout.fillWidth: true
                visible: settingsVM.disabledRules.length > 0

                ColumnLayout {
                    width: parent.width
                    spacing: 10

                    Text {
                        text: "Kapatılan Kurallar (" + settingsVM.disabledRules.length + ")"
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeBase
                        font.bold: true
                        renderType: Text.NativeRendering
                    }
                    Text {
                        text: "Bu kurallar analizde yok sayılır (Sorunlar sayfasından kapatılanlar). Geri açmak için kurala tıklayın."
                        color: AppTheme.textSecondary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        renderType: Text.NativeRendering
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: settingsVM.disabledRules

                            CustomButton {
                                text: modelData.title + "  ×"
                                variant: "secondary"
                                onClicked: settingsVM.enableRule(modelData.id)
                            }
                        }
                    }
                }
            }

            // ── 6. Yapay zeka ajan görevleri ──
            CardFrame {
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    RowLayout {
                        spacing: 8
                        SvgIcon {
                            source: AppIcons.document
                            size: 16
                            color: AppTheme.accent
                        }
                        Text {
                            text: AppStrings.agentTaskExportTitle
                            color: AppTheme.textPrimary
                            font.family: AppTheme.fontFamily
                            font.pixelSize: AppTheme.fontSizeBase
                            font.bold: true
                            renderType: Text.NativeRendering
                        }
                    }

                    Text {
                        text: AppStrings.agentTaskExportDesc + " Dalga sırası: sırlar (insan) → güvenlik → güvenilirlik → temizlik → hijyen → test → refactor."
                        color: AppTheme.textSecondary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        renderType: Text.NativeRendering
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: AppTheme.border
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text {
                                text: "Çıktı Dizini" + (settingsVM.agentOutputDirIsCustom ? "" : " (varsayılan: proje dışında)")
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                renderType: Text.NativeRendering
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 36
                                    radius: AppTheme.radiusSmall
                                    color: AppTheme.surface
                                    border.color: AppTheme.border
                                    border.width: 1

                                    Text {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        verticalAlignment: Text.AlignVCenter
                                        text: settingsVM.agentOutputDir
                                        color: AppTheme.textPrimary
                                        font.family: AppTheme.fontFamily
                                        font.pixelSize: AppTheme.fontSizeSmall
                                        elide: Text.ElideMiddle
                                        renderType: Text.NativeRendering
                                    }
                                }

                                CustomButton {
                                    text: AppStrings.selectFolder
                                    iconSource: AppIcons.folder
                                    variant: "secondary"
                                    onClicked: agentTaskFolderDialog.open()
                                }

                                CustomButton {
                                    text: "Varsayılan"
                                    variant: "secondary"
                                    visible: settingsVM.agentOutputDirIsCustom
                                    onClicked: settingsVM.setAgentOutputDir("")
                                }
                            }
                        }

                        ColumnLayout {
                            spacing: 4
                            Text {
                                text: AppStrings.agentBatchSize
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                renderType: Text.NativeRendering
                            }

                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "secondary"
                                    Layout.preferredWidth: 36
                                    onClicked: settingsVM.adjustAgentBatchSize(-5)
                                }
                                Text {
                                    text: settingsVM.agentBatchSize.toString()
                                    color: AppTheme.accent
                                    font.family: AppTheme.fontFamily
                                    font.bold: true
                                    Layout.preferredWidth: 44
                                    horizontalAlignment: Text.AlignHCenter
                                    renderType: Text.NativeRendering
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "secondary"
                                    Layout.preferredWidth: 36
                                    onClicked: settingsVM.adjustAgentBatchSize(5)
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        CustomButton {
                            text: AppStrings.exportAgentTasksBtn
                            iconSource: AppIcons.download
                            variant: "primary"
                            enabled: appVM.hasProject
                            onClicked: settingsVM.exportAgentTasks()
                        }

                        CustomButton {
                            text: AppStrings.verifyAgentTasksBtn
                            iconSource: AppIcons.shield
                            variant: "secondary"
                            enabled: appVM.hasProject
                            onClicked: settingsVM.verifyAgentTasks()
                        }
                    }

                    // Son işlem sonucu
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: resultLayout.implicitHeight + 24
                        radius: AppTheme.radiusSmall
                        color: AppTheme.bgSecondary
                        border.color: AppTheme.border
                        border.width: 1
                        visible: root.agentKind !== ""

                        ColumnLayout {
                            id: resultLayout
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6

                            Text {
                                text: root.agentKind === "export"
                                      ? ("Görevler oluşturuldu: " + root.agentResult.totalTasks + " görev, " + root.agentResult.totalItems + " öğe")
                                      : ("Doğrulama: " + root.agentResult.closed + " öğe kapandı, "
                                         + root.agentResult.reduced + " azaldı, " + root.agentResult.open + " açık ("
                                         + root.agentResult.total + " öğeden)")
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                renderType: Text.NativeRendering
                            }

                            Text {
                                visible: root.agentKind === "verify" && root.agentResult.newCount > 0
                                text: "Değişikliklerin yeni çıkardığı bulgu: " + root.agentResult.newCount
                                color: AppTheme.warning
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                renderType: Text.NativeRendering
                            }

                            Text {
                                visible: root.agentKind === "verify" && (root.agentResult.warning || "") !== ""
                                text: root.agentResult.warning || ""
                                color: AppTheme.warning
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                renderType: Text.NativeRendering
                            }

                            Text {
                                visible: root.agentKind === "export"
                                text: "Ajana README.md dosyasını verin; Dalga 0 görevleri insan aksiyonudur (sır yenileme, lisans kararı)."
                                color: AppTheme.textSecondary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                renderType: Text.NativeRendering
                            }

                            CustomButton {
                                text: "Klasörü Aç"
                                iconSource: AppIcons.folder
                                variant: "secondary"
                                onClicked: appVM.openPath(root.agentResult.outputDir || "")
                            }
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: 30 }
        }
    }
}
