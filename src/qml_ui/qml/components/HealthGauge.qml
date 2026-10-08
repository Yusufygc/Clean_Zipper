import QtQuick
import "../singletons"

Item {
    id: root

    property int score: 0
    property string status: "—"
    property int gaugeSize: 180

    implicitWidth: gaugeSize
    implicitHeight: gaugeSize

    property real animatedScore: 0
    Behavior on animatedScore {
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }

    onScoreChanged: animatedScore = score
    onAnimatedScoreChanged: canvas.requestPaint()

    readonly property color scoreColor: {
        if (animatedScore >= 90) return AppTheme.success
        if (animatedScore >= 75) return AppTheme.accent
        if (animatedScore >= 60) return AppTheme.warning
        return AppTheme.danger
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()

            var centerX = width / 2
            var centerY = height / 2
            var radius = (Math.min(width, height) / 2) - 14
            var lineWidth = 12

            var startAngle = Math.PI * 0.75
            var endAngle = Math.PI * 2.25
            var totalAngle = endAngle - startAngle

            // 1. Arka plan çemberi
            ctx.beginPath()
            ctx.arc(centerX, centerY, radius, startAngle, endAngle, false)
            ctx.strokeStyle = AppTheme.isDark ? "#1E293B" : "#E2E8F0"
            ctx.lineWidth = lineWidth
            ctx.lineCap = "round"
            ctx.stroke()

            // 2. İlerleme yayı
            if (root.animatedScore > 0) {
                var currentAngle = startAngle + (totalAngle * Math.min(Math.max(root.animatedScore, 0), 100) / 100)
                ctx.beginPath()
                ctx.arc(centerX, centerY, radius, startAngle, currentAngle, false)
                ctx.strokeStyle = root.scoreColor.toString()
                ctx.lineWidth = lineWidth
                ctx.lineCap = "round"
                ctx.stroke()
            }
        }
    }

    // Merkez Bilgi Bloğu
    Column {
        anchors.centerIn: parent
        spacing: 2

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(root.animatedScore).toString()
            color: AppTheme.textPrimary
            font.family: AppTheme.fontFamily
            font.pixelSize: 38
            font.bold: true
            renderType: Text.NativeRendering
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "SKOR / 100"
            color: AppTheme.textMuted
            font.family: AppTheme.fontFamily
            font.pixelSize: 10
            font.bold: true
            font.letterSpacing: 1
            renderType: Text.NativeRendering
        }

        Badge {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.status !== "" ? root.status : "—"
            textColor: root.scoreColor
            badgeColor: AppTheme.isDark ? "#111827" : "#F1F5F9"
            borderColor: root.scoreColor
            fontSize: 12
        }
    }
}
