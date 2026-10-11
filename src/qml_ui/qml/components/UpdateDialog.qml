import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons"

// "Yeni sürüm var" penceresi (XP iletişim kutusu): sürüm notları, kurulum dosyası bilgisi; Güncelle / Sonra / Bu Sürümü Atla.
// "Güncelle": kurulum dosyası indirilir (ilerleme çubuğu), SHA-256 doğrulanır, kurulum başlar ve uygulama kapanır.
Popup {
    id: root
    objectName: "updateDialog"

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    padding: 0
    width: Math.min(560, parent ? parent.width - 40 : 560)
    closePolicy: updateVM.isDownloading ? Popup.NoAutoClose : Popup.CloseOnEscape       // indirme sürerken kapanmaz

    Overlay.modal: Rectangle { color: "#66000000" }

    background: Rectangle {
        color: AppTheme.bg
        border.color: AppTheme.titleBorder
        border.width: 2
        radius: AppTheme.radiusCard
    }

    contentItem: ColumnLayout {
        spacing: 0
        Accessible.role: Accessible.Dialog
        Accessible.name: "Yeni sürüm var: " + updateVM.latestVersion

        Rectangle {                                                    // XP başlık şeridi
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            radius: AppTheme.radiusCard
            gradient: Gradient {
                GradientStop { position: 0.0; color: AppTheme.titleTop }
                GradientStop { position: 1.0; color: AppTheme.titleBottom }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 14
                text: "Yeni sürüm var"
                color: AppTheme.titleText
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeBase
                font.bold: true
                renderType: Text.NativeRendering
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 18
            spacing: 12

            Text {
                objectName: "updateHeadline"
                text: "GitClean Archiver v" + updateVM.latestVersion + " yayınlandı"
                color: AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeMedium
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Text {
                text: "Kurulu sürüm: v" + updateVM.currentVersion
                      + (updateVM.publishedDate !== "" ? "  ·  Yayın tarihi: " + updateVM.publishedDate : "")
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Rectangle {                                                // sürüm notları: düz metin (bağlantı / biçim çalıştırılmaz)
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(220, Math.max(60, notes.implicitHeight + 20))
                visible: updateVM.releaseNotes !== ""
                color: AppTheme.surface
                border.color: AppTheme.border
                border.width: 1

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 1
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.vertical: ThemedScrollBar { }

                    Text {
                        id: notes
                        objectName: "updateNotes"
                        width: parent.width - AppTheme.scrollGutter
                        x: 10
                        y: 10
                        text: updateVM.releaseNotes
                        textFormat: Text.PlainText
                        color: AppTheme.textPrimary
                        font.family: AppTheme.fontFamily
                        font.pixelSize: AppTheme.fontSizeSmall
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }
                }
            }

            Text {
                text: "İndirilecek dosya: " + updateVM.installerLabel
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Text {
                text: "Güncelle: kurulum dosyası indirilir ve SHA-256 özeti doğrulanır, uygulama kapanır, kurulum üstüne yazar ve uygulama yeniden açılır. Ayarlarınız ve yedekleriniz korunur."
                color: AppTheme.textMuted
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Rectangle {                                                // indirme ilerlemesi
                objectName: "downloadProgress"
                Layout.fillWidth: true
                Layout.preferredHeight: 10
                visible: updateVM.isDownloading
                color: AppTheme.trackBg
                border.color: AppTheme.border
                border.width: 1

                Rectangle {
                    width: parent.width * (updateVM.downloadProgress / 100)
                    height: parent.height
                    color: AppTheme.accent
                }
            }

            Text {
                objectName: "updateError"
                visible: updateVM.errorMessage !== ""
                text: updateVM.errorMessage
                color: updateVM.isWaitingForWindows ? AppTheme.textSecondary : AppTheme.danger
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 4
                spacing: 8

                CustomButton {
                    objectName: "skipVersionButton"
                    enabled: !updateVM.isDownloading
                    text: "Bu Sürümü Atla"
                    variant: "ghost"
                    onClicked: { updateVM.skipVersion(); root.close() }
                }

                Item { Layout.fillWidth: true }

                CustomButton {
                    objectName: "stopWaitingButton"
                    visible: updateVM.isWaitingForWindows
                    text: "Beklemeyi Bırak"
                    variant: "secondary"
                    onClicked: updateVM.stopWaiting()
                }

                CustomButton {
                    objectName: "releasePageButton"
                    visible: updateVM.errorMessage !== ""
                    text: "Sürüm Sayfası"
                    variant: "ghost"
                    onClicked: updateVM.openReleasePage()
                }

                CustomButton {
                    objectName: "laterButton"
                    enabled: !updateVM.isDownloading
                    text: "Sonra"
                    variant: "secondary"
                    onClicked: root.close()
                }

                CustomButton {
                    objectName: "downloadButton"
                    enabled: !updateVM.isDownloading
                    text: updateVM.isWaitingForWindows ? "Windows bekleniyor…"
                          : (updateVM.isDownloading ? "İndiriliyor… %" + updateVM.downloadProgress : (updateVM.canInstall ? "Güncelle" : "Sürüm Sayfası"))
                    variant: "primary"
                    iconSource: AppIcons.download
                    onClicked: updateVM.startUpdate()
                }
            }
        }
    }
}
