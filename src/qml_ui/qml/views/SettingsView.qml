import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "../singletons"
import "../components"

Item {
    id: root

    property string exportTargetDir: appVM.hasProject ? (appVM.projectPath + "/agent_tasks") : ""
    property string bannerMessage: ""
    property string bannerType: "success"
    property bool bannerVisible: false

    FolderDialog {
        id: agentTaskFolderDialog
        title: "Ajan Görev Paketinin Kaydedileceği Dizini Seçin"
    }

    Connections {
        target: settingsVM
        function onTaskExportFinished(result) {
            root.bannerMessage = "Ajan görevleri başarıyla üretildi."
            root.bannerType = "success"
            root.bannerVisible = true
        }
        function onTaskExportError(errMsg) {
            root.bannerMessage = "Hata: " + errMsg
            root.bannerType = "danger"
            root.bannerVisible = true
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 20

            // 1. Üst Başlık
            RowLayout {
                Layout.fillWidth: true
                Text { text: AppStrings.tabSettings; font.bold: true }
                CustomButton {
                    text: AppStrings.applySettingsBtn
                    onClicked: settingsVM.applySettings()
                }
            }

            // Bildirim Çubuğu
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                radius: AppTheme.radiusSmall
                visible: root.bannerVisible
                color: root.bannerType === "danger" ? AppTheme.dangerBg : AppTheme.successBg
                border.color: root.bannerType === "danger" ? AppTheme.danger : AppTheme.success
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    SvgIcon {
                        source: root.bannerType === "danger" ? AppIcons.alert : AppIcons.check
                        size: 16
                        color: root.bannerType === "danger" ? AppTheme.danger : AppTheme.success
                    }

                    Text {
                        text: root.bannerMessage
                        color: root.bannerType === "danger" ? AppTheme.danger : AppTheme.success
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }

            // 2. Git Kartı
            CardFrame {
                Layout.fillWidth: true
                CheckBox {
                    checked: settingsVM.respectGitignore
                    onToggled: settingsVM.setRespectGitignore(checked)
                }
            }

            // 3. Eşikler Kartı
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
                    }

                    GridLayout {
                        columns: 2
                        rowSpacing: 12
                        columnSpacing: 24
                        Layout.fillWidth: true

                        // Cyclomatic
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: AppStrings.cyclomaticThreshold
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "outline"
                                    onClicked: settingsVM.setCyclomatic(settingsVM.cyclomatic - 1)
                                }
                                Text {
                                    text: settingsVM.cyclomatic.toString()
                                    color: AppTheme.accent
                                    font.bold: true
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "outline"
                                    onClicked: settingsVM.setCyclomatic(settingsVM.cyclomatic + 1)
                                }
                            }
                        }

                        // Cognitive
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: AppStrings.cognitiveThreshold
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "outline"
                                    onClicked: settingsVM.setCognitive(settingsVM.cognitive - 1)
                                }
                                Text {
                                    text: settingsVM.cognitive.toString()
                                    color: AppTheme.accent
                                    font.bold: true
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "outline"
                                    onClicked: settingsVM.setCognitive(settingsVM.cognitive + 1)
                                }
                            }
                        }

                        // Function Lines
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: AppStrings.functionLinesThreshold
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "outline"
                                    onClicked: settingsVM.setFunctionLines(settingsVM.functionLines - 5)
                                }
                                Text {
                                    text: settingsVM.functionLines.toString()
                                    color: AppTheme.accent
                                    font.bold: true
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "outline"
                                    onClicked: settingsVM.setFunctionLines(settingsVM.functionLines + 5)
                                }
                            }
                        }

                        // Class Lines
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: AppStrings.classLinesThreshold
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "outline"
                                    onClicked: settingsVM.setClassLines(settingsVM.classLines - 25)
                                }
                                Text {
                                    text: settingsVM.classLines.toString()
                                    color: AppTheme.accent
                                    font.bold: true
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "outline"
                                    onClicked: settingsVM.setClassLines(settingsVM.classLines + 25)
                                }
                            }
                        }

                        // File Lines
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: AppStrings.fileLinesThreshold
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "outline"
                                    onClicked: settingsVM.setFileLines(settingsVM.fileLines - 50)
                                }
                                Text {
                                    text: settingsVM.fileLines.toString()
                                    color: AppTheme.accent
                                    font.bold: true
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "outline"
                                    onClicked: settingsVM.setFileLines(settingsVM.fileLines + 50)
                                }
                            }
                        }
                    }
                }
            }

            // 4. Analizörler
            CardFrame {
                Layout.fillWidth: true
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

                                CheckBox {
                                    checked: modelData.enabled
                                    onToggled: settingsVM.toggleAnalyzer(modelData.id, checked)
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    RowLayout {
                                        spacing: 8
                                        Text {
                                            text: modelData.name
                                            color: modelData.enabled ? AppTheme.textPrimary : AppTheme.textMuted
                                            font.family: AppTheme.fontFamily
                                            font.pixelSize: AppTheme.fontSizeSmall
                                            font.bold: true
                                            renderType: Text.NativeRendering
                                        }
                                        Badge {
                                            text: modelData.id
                                            badgeColor: AppTheme.surfaceHover
                                            textColor: AppTheme.textMuted
                                            fontSize: 10
                                        }
                                    }

                                    Text {
                                        text: modelData.description
                                        color: AppTheme.textSecondary
                                        font.family: AppTheme.fontFamily
                                        font.pixelSize: 11
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

            // 5. Yapay Zeka (AI Agent) Görev Dağıtımı
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
                        }
                    }

                    Text {
                        text: AppStrings.agentTaskExportDesc
                        color: AppTheme.textSecondary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: AppTheme.border
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        // Hedef Dizin
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text {
                                text: "Hedef Çıktı Dizini"
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
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
                                        text: root.exportTargetDir !== "" ? root.exportTargetDir : "Hedef dizin belirtilmedi..."
                                        color: root.exportTargetDir !== "" ? AppTheme.textPrimary : AppTheme.textMuted
                                        font.family: AppTheme.fontFamily
                                        font.pixelSize: AppTheme.fontSizeSmall
                                        elide: Text.ElideMiddle
                                    }
                                }

                                CustomButton {
                                    text: AppStrings.selectFolder
                                    iconSource: AppIcons.folder
                                    variant: "outline"
                                    onClicked: agentTaskFolderDialog.open()
                                }
                            }
                        }

                        // Batch Size
                        ColumnLayout {
                            spacing: 4
                            Text {
                                text: AppStrings.agentBatchSize
                                color: AppTheme.textPrimary
                                font.family: AppTheme.fontFamily
                                font.pixelSize: AppTheme.fontSizeSmall
                                font.bold: true
                            }

                            RowLayout {
                                spacing: 4
                                CustomButton {
                                    text: "-"
                                    variant: "outline"
                                    onClicked: settingsVM.setAgentBatchSize(settingsVM.agentBatchSize - 5)
                                }
                                Text {
                                    text: settingsVM.agentBatchSize.toString()
                                    color: AppTheme.accent
                                    font.bold: true
                                }
                                CustomButton {
                                    text: "+"
                                    variant: "outline"
                                    onClicked: settingsVM.setAgentBatchSize(settingsVM.agentBatchSize + 5)
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
                            enabled: appVM.hasProject && root.exportTargetDir !== ""
                            onClicked: settingsVM.exportAgentTasks(root.exportTargetDir)
                        }

                        CustomButton {
                            text: AppStrings.verifyAgentTasksBtn
                            iconSource: AppIcons.shield
                            variant: "secondary"
                            enabled: appVM.hasProject && root.exportTargetDir !== ""
                            onClicked: settingsVM.verifyAgentTasks(root.exportTargetDir)
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: 30 }
        }
    }
}
