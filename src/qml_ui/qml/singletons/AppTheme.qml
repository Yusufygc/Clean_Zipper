import QtQuick

pragma Singleton

// Retro Windows XP (Luna) teması: bej pencere zemini, mavi gradyan başlık, gradyanlı düğmeler, turuncu üzerine gelme.
// Yazı tipi güncel ve okunaklıdır (Segoe UI). Koyu tema, aynı geometriyle koyu bir "Royale Noir" benzeri palettir.
QtObject {
    id: theme

    property bool isDark: false

    function toggleTheme() {
        isDark = !isDark
    }

    // ── Zemin ve yüzeyler ──
    readonly property color bg: isDark ? "#0B0F17" : "#ECE9D8"               // Luna bej pencere zemini
    readonly property color bgSecondary: isDark ? "#111827" : "#E3DFC9"
    readonly property color surface: isDark ? "#1E293B" : "#FFFFFF"           // liste / giriş / kart yüzeyi
    readonly property color surfaceHover: isDark ? "#283548" : "#E8F0FD"
    readonly property color surfaceActive: isDark ? "#334155" : "#C9DBF8"
    readonly property color surfaceElevated: isDark ? "#1A2234" : "#F5F3E8"   // durum çubuğu, açılır liste

    // ── Bileşen yüzeyleri: ilerleme izi, ikon kutusu / rozet, kod bloğu (XP'de bej tonları) ──
    readonly property color trackBg: isDark ? "#1E293B" : "#DEDACA"
    readonly property color tileBg: isDark ? "#111827" : "#ECE9D8"
    readonly property color codeBg: isDark ? "#111827" : "#F7F5EC"

    // ── Kenarlıklar ──
    readonly property color border: isDark ? "#2E3B4E" : "#919B9C"            // XP sekme / liste kenarı
    readonly property color borderSubtle: isDark ? "#1E293B" : "#D5D2BF"
    readonly property color borderStrong: isDark ? "#475569" : "#003C74"      // düğme kenarı (koyu lacivert)
    readonly property int borderWidthControl: 1
    readonly property int scrollGutter: 14

    // ── Metin (koyu zeminde açık, bej / beyaz üstünde koyu: okunaklı) ──
    readonly property color textPrimary: isDark ? "#FFFFFF" : "#101010"
    readonly property color textSecondary: isDark ? "#E2E8F0" : "#2B2B2B"
    readonly property color textMuted: isDark ? "#CBD5E1" : "#545454"
    readonly property color textInverse: isDark ? "#0F172A" : "#FFFFFF"

    // ── Vurgu ──
    readonly property color primary: isDark ? "#5B9BFF" : "#316AC5"           // XP seçim mavisi
    readonly property color primaryHover: isDark ? "#60A5FA" : "#1F4FA0"
    readonly property color accent: isDark ? "#38BDF8" : "#0A55D8"            // Luna mavisi
    readonly property color accentHover: isDark ? "#7DD3FC" : "#0842A8"

    readonly property color success: isDark ? "#10B981" : "#2E7D32"
    readonly property color successBg: isDark ? "#064E3B" : "#E4F3E4"
    readonly property color warning: isDark ? "#F59E0B" : "#B45309"
    readonly property color danger: isDark ? "#F87171" : "#C0392B"
    readonly property color dangerBg: isDark ? "#7F1D1D" : "#FBE7E3"
    readonly property color info: isDark ? "#6366F1" : "#4F46E5"

    // ── Başlık çubuğu: Luna mavi gradyan (koyu temada lacivert) ──
    readonly property color titleTop: isDark ? "#1B3A78" : "#0A5BEB"
    readonly property color titleMid: isDark ? "#142C5C" : "#1C72E8"
    readonly property color titleBottom: isDark ? "#0E1F45" : "#0B4FD0"
    readonly property color titleBorder: isDark ? "#0A1530" : "#0831A0"
    readonly property color titleText: "#FFFFFF"

    // ── Sekmeler: pasif sekme mavi, seçili sekme içerikle aynı bej (içeriğe kaynaşır), üstte turuncu çizgi ──
    readonly property color tabIdleTop: isDark ? "#223B6E" : "#2F6FE0"
    readonly property color tabIdleBottom: isDark ? "#182C55" : "#1F58C4"
    readonly property color tabIdleHover: isDark ? "#2D4A87" : "#3571E3"
    readonly property color tabIdleBorder: isDark ? "#0A1530" : "#0831A0"
    readonly property color tabIdleText: "#FFFFFF"
    readonly property color tabActiveBg: bg
    readonly property color tabActiveText: textPrimary
    readonly property color tabActiveLine: "#FFC73C"                          // XP seçili sekme üst vurgusu

    // ── Düğme gradyanları (üst, alt, kenar) ──
    readonly property color btnTop: isDark ? "#334155" : "#FFFFFF"
    readonly property color btnBottom: isDark ? "#1E293B" : "#D6D0C5"
    readonly property color btnPressTop: isDark ? "#1E293B" : "#CBC7BA"
    readonly property color btnPressBottom: isDark ? "#334155" : "#E7E3D6"
    readonly property color btnHoverBorder: "#F8B330"                         // XP turuncu üzerine gelme çerçevesi
    readonly property color btnDisabledText: isDark ? "#8A9BB4" : "#6F6C60"
    readonly property color btnDisabledFill: isDark ? "#1A2234" : "#F4F2EA"
    readonly property color btnDisabledBorder: isDark ? "#2E3B4E" : "#C9C6B6"

    readonly property color startTop: "#278527"                               // yeşil "Başlat" düğmesi (birincil eylem); beyaz yazıyla en az 4.5:1
    readonly property color startBottom: "#1F6B1F"
    readonly property color startBorder: "#14501C"

    // Vurgu (mavi) ve tehlike (kırmızı) düğmeleri: beyaz yazıyla her iki uçta en az 4.5:1
    readonly property color accentBtnTop: "#2A6FDB"
    readonly property color accentBtnBottom: "#1550B8"
    readonly property color accentBtnBorder: "#0A3A99"
    readonly property color dangerBtnTop: "#CC4A32"
    readonly property color dangerBtnBottom: "#A8321A"
    readonly property color dangerBtnBorder: "#8E2A12"

    // Klavye odak halkası (Tab ile odaklanan öğenin çevresi)
    readonly property color focusRing: isDark ? "#FFFFFF" : "#101010"

    // Şiddet renkleri: rozet yazısı (onSeverity) her zeminle en az 4,5:1 (açık: beyaz yazı koyu zemin, koyu: koyu yazı açık zemin)
    readonly property color severityHigh: isDark ? "#FB923C" : "#C2410C"
    readonly property color onSeverity: isDark ? "#0F172A" : "#FFFFFF"

    function severityColor(name) {
        switch (String(name).toUpperCase()) {
        case "CRITICAL": return danger
        case "HIGH": return severityHigh
        case "MEDIUM": return warning
        case "LOW": return primary
        default: return success
        }
    }

    // ── Geometri: XP köşeleri küçük yarıçaplıdır ──
    readonly property int radiusSmall: 3
    readonly property int radiusBase: 3
    readonly property int radiusCard: 4

    // ── Tipografi: güncel, okunaklı ──
    readonly property string fontFamily: "Segoe UI"
    readonly property int fontSizeSmall: 12
    readonly property int fontSizeBase: 13
    readonly property int fontSizeMedium: 15
    readonly property int fontSizeLarge: 18
    readonly property int fontSizeTitle: 22

    // ── Animasyon ──
    readonly property int animFast: 120
    readonly property int animNormal: 200
}
