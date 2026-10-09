import QtQuick

pragma Singleton

QtObject {
    id: theme

    // Aktif tema durumu (Varsayılan Koyu Tema)
    property bool isDark: true

    function toggleTheme() {
        isDark = !isDark
    }

    // Renk Paleti - Canlı ve Koyu/Açık Dinamik
    readonly property color bg: isDark ? "#0B0F17" : "#F8FAFC"
    readonly property color bgSecondary: isDark ? "#111827" : "#F1F5F9"
    readonly property color surface: isDark ? "#1E293B" : "#FFFFFF"
    readonly property color surfaceHover: isDark ? "#283548" : "#F1F5F9"
    readonly property color surfaceActive: isDark ? "#334155" : "#E2E8F0"
    readonly property color surfaceElevated: isDark ? "#1A2234" : "#FFFFFF"

    // Kenarlıklar
    readonly property color border: isDark ? "#2E3B4E" : "#E2E8F0"
    readonly property color borderSubtle: isDark ? "#1E293B" : "#F1F5F9"

    // Metin Renkleri: koyu temada soluk gri yok; ikincil metin de parlak ve okunaklı (WCAG AA üstü kontrast)
    readonly property color textPrimary: isDark ? "#FFFFFF" : "#0F172A"
    readonly property color textSecondary: isDark ? "#E2E8F0" : "#334155"
    readonly property color textMuted: isDark ? "#CBD5E1" : "#475569"
    readonly property color textInverse: isDark ? "#0F172A" : "#FFFFFF"

    // Durum ve Vurgu Renkleri
    readonly property color primary: isDark ? "#3B82F6" : "#2563EB"
    readonly property color primaryHover: isDark ? "#60A5FA" : "#1D4ED8"
    readonly property color accent: isDark ? "#38BDF8" : "#0284C7"
    readonly property color accentHover: isDark ? "#7DD3FC" : "#0369A1"

    readonly property color success: isDark ? "#10B981" : "#059669"
    readonly property color successBg: isDark ? "#064E3B" : "#ECFDF5"
    
    readonly property color warning: isDark ? "#F59E0B" : "#D97706"
    
    readonly property color danger: isDark ? "#EF4444" : "#DC2626"
    readonly property color dangerBg: isDark ? "#7F1D1D" : "#FEF2F2"
    
    readonly property color info: isDark ? "#6366F1" : "#4F46E5"

    // Geometri & Yuvarlaklık
    readonly property int radiusSmall: 4
    readonly property int radiusBase: 8
    readonly property int radiusCard: 12

    // Tipografi
    readonly property string fontFamily: "Segoe UI"
    readonly property int fontSizeSmall: 12
    readonly property int fontSizeBase: 13
    readonly property int fontSizeMedium: 15
    readonly property int fontSizeLarge: 18
    readonly property int fontSizeTitle: 22

    // Animasyon
    readonly property int animFast: 150
    readonly property int animNormal: 250
}
