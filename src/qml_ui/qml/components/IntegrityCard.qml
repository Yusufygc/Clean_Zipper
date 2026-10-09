import QtQuick
import QtQuick.Layouts
import "../singletons"

CardFrame {
    id: root

    property var failedAnalyzers: []
    property var skippedFiles: ({})
    property var skippedDetail: []
    property int ignoredGitignore: 0
    property bool gitignoreApplied: true

    padding: 16

    ColumnLayout {
        width: parent.width
        spacing: 12

        // Başlık
        RowLayout {
            spacing: 8
            SvgIcon {
                source: AppIcons.shield
                size: 16
                color: AppTheme.accent
            }
            Text {
                text: AppStrings.analysisIntegrity
                color: AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeBase
                font.bold: true
                renderType: Text.NativeRendering
            }
        }

        // Hata veren analizörler uyarısı
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            radius: AppTheme.radiusSmall
            color: root.failedAnalyzers.length > 0 ? AppTheme.dangerBg : AppTheme.successBg
            border.color: root.failedAnalyzers.length > 0 ? AppTheme.danger : AppTheme.success
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                SvgIcon {
                    source: root.failedAnalyzers.length > 0 ? AppIcons.alert : AppIcons.check
                    size: 16
                    color: root.failedAnalyzers.length > 0 ? AppTheme.danger : AppTheme.success
                }

                Text {
                    text: root.failedAnalyzers.length > 0 
                          ? ("Eksik Sonuç: " + root.failedAnalyzers.join(", ") + " hata verdi")
                          : "Çalışan tüm analizörler eksiksiz tamamlandı"
                    color: root.failedAnalyzers.length > 0 ? AppTheme.danger : AppTheme.success
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    renderType: Text.NativeRendering
                }
            }
        }

        // Bilgi Grid'i: Gitignore ve Atlanan Dosyalar
        GridLayout {
            columns: 2
            rowSpacing: 8
            columnSpacing: 16
            Layout.fillWidth: true

            // Gitignore Filtresi
            Text {
                text: AppStrings.gitignoreIgnored + ":"
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
            }
            Badge {
                text: root.ignoredGitignore.toString() + " dosya / klasör"
                textColor: AppTheme.textPrimary
                badgeColor: AppTheme.surfaceActive
            }

            // Atlanan Dosyalar (Boyut, parse, okunamayan)
            Text {
                text: AppStrings.skippedFiles + ":"
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
            }
            RowLayout {
                spacing: 4
                property int totalSkipped: {
                    var sum = 0
                    for (var k in root.skippedFiles) {
                        sum += root.skippedFiles[k]
                    }
                    return sum
                }

                Badge {
                    text: parent.totalSkipped.toString() + " dosya"
                    textColor: parent.totalSkipped > 0 ? AppTheme.warning : AppTheme.textSecondary
                    badgeColor: AppTheme.surfaceActive
                }
            }
        }

        // Atlanan dosyaların nedenleri
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            visible: root.skippedDetail.length > 0

            Repeater {
                model: root.skippedDetail

                Text {
                    text: "• " + modelData.label + ": " + modelData.count
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    renderType: Text.NativeRendering
                }
            }
        }

        Text {
            text: "Python dışı diller (JS/TS, C#, Rust, Go vb.) sözlüksel yaklaşım ile taranır."
            color: AppTheme.textMuted
            font.family: AppTheme.fontFamily
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            renderType: Text.NativeRendering
        }
    }
}
