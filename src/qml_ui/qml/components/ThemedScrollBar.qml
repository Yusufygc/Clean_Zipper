import QtQuick
import QtQuick.Controls.Basic
import "../singletons"

// Temaya uyan dikey kaydırma çubuğu. Varsayılan Qt çubuğu açık temada siyah, koyu temada beyazdı ve içeriğin üstüne
// biniyordu; içerik `AppTheme.scrollGutter` kadar boşluk bırakır, çubuk bu boşlukta durur.
ScrollBar {
    id: root
    policy: ScrollBar.AsNeeded
    implicitWidth: AppTheme.scrollGutter - 4
    minimumSize: 0.08

    // XP kaydırma çubuğu: açık mavi gövde, ince mavi kenar; üzerine gelince turuncu
    contentItem: Rectangle {
        implicitWidth: AppTheme.scrollGutter - 4
        radius: 3
        color: root.pressed ? AppTheme.surfaceActive : (root.hovered ? "#DCE8FF" : (AppTheme.isDark ? AppTheme.border : "#C6D8FA"))
        border.width: 1
        border.color: root.hovered || root.pressed ? AppTheme.btnHoverBorder : (AppTheme.isDark ? AppTheme.borderStrong : "#8EA7E0")
        opacity: root.size < 1 ? 1 : 0
    }
    background: Rectangle {
        implicitWidth: AppTheme.scrollGutter - 4
        color: AppTheme.isDark ? AppTheme.surfaceHover : "#F3F1E6"
        border.width: 1
        border.color: AppTheme.borderSubtle
        opacity: root.size < 1 ? 1 : 0
    }
}
