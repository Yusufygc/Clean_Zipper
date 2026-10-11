import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons"

// "Kur / Güncelle" penceresi: indirilen exe kendini kurar (ayrı kurulum programı yok; Windows Akıllı Uygulama Denetimi imzasız
// kurulum programlarını engeller). Yönetici hakkı gerekmez; "Kurmadan Çalıştır" taşınabilir kullanımı sürdürür.
Popup {
    id: root
    objectName: "installDialog"

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    padding: 0
    width: Math.min(540, parent ? parent.width - 40 : 540)
    closePolicy: Popup.CloseOnEscape

    Overlay.modal: Rectangle { color: "#66000000" }

    background: Rectangle {
        color: AppTheme.bg
        border.color: AppTheme.titleBorder
        border.width: 2
        radius: AppTheme.radiusCard
    }

    readonly property bool isUpdate: installVM.mode === "update"

    contentItem: ColumnLayout {
        spacing: 0
        Accessible.role: Accessible.Dialog
        Accessible.name: root.isUpdate ? "GitClean Archiver güncelleme" : "GitClean Archiver kurulum"

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
                text: root.isUpdate ? "Güncelleme" : "Kurulum"
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
                objectName: "installHeadline"
                text: root.isUpdate
                      ? "v" + installVM.installedVersion + " sürümünden v" + installVM.currentVersion + " sürümüne güncellensin mi?"
                      : "GitClean Archiver v" + installVM.currentVersion + " bu bilgisayara kurulsun mu?"
                color: AppTheme.textPrimary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeMedium
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Text {
                text: "Kurulum klasörü:"
                color: AppTheme.textSecondary
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                renderType: Text.NativeRendering
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                color: AppTheme.surface
                border.color: AppTheme.border
                border.width: 1

                Text {
                    objectName: "installDir"
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    verticalAlignment: Text.AlignVCenter
                    text: installVM.installDir
                    elide: Text.ElideMiddle
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }
            }

            RowLayout {
                spacing: 10
                visible: !root.isUpdate

                AppCheckBox {
                    objectName: "desktopShortcutCheck"
                    accessibleName: "Masaüstü kısayolu oluştur"
                    checked: installVM.desktopShortcut
                    onToggled: installVM.setDesktopShortcut(checked)
                }
                Text {
                    text: "Masaüstü kısayolu oluştur"
                    color: AppTheme.textPrimary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }
            }

            Text {
                text: "Yönetici hakkı gerekmez. Başlat menüsüne kısayol eklenir, Windows'ta \"Uygulamalar ve özellikler\" listesine girer; "
                      + "ayarlarınız ve yedekleriniz (~/.gitclean) güncellemede ve kaldırmada korunur. Kurmadan da çalıştırabilirsiniz."
                color: AppTheme.textMuted
                font.family: AppTheme.fontFamily
                font.pixelSize: AppTheme.fontSizeSmall
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                renderType: Text.NativeRendering
            }

            Text {
                objectName: "installError"
                visible: installVM.errorText !== ""
                text: installVM.errorText
                color: AppTheme.danger
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

                AppCheckBox {
                    id: neverAsk
                    objectName: "neverAskCheck"
                    accessibleName: "Bir daha sorma"
                }
                Text {
                    text: "Bir daha sorma"
                    color: AppTheme.textSecondary
                    font.family: AppTheme.fontFamily
                    font.pixelSize: AppTheme.fontSizeSmall
                    renderType: Text.NativeRendering
                }

                Item { Layout.fillWidth: true }

                CustomButton {
                    objectName: "runPortableButton"
                    text: "Kurmadan Çalıştır"
                    variant: "secondary"
                    onClicked: { installVM.decline(neverAsk.checked); root.close() }
                }

                CustomButton {
                    objectName: "installButton"
                    text: root.isUpdate ? "Güncelle" : "Kur"
                    variant: "primary"
                    onClicked: installVM.install()
                }
            }
        }
    }
}
