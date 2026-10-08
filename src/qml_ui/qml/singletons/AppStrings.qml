import QtQuick

pragma Singleton

QtObject {
    id: strings

    // Uygulama Genel
    readonly property string appTitle: "GitClean Archiver Pro"
    readonly property string appVersion: "v2.0.0"

    // Sekme Başlıkları
    readonly property string tabDashboard: "Gösterge Paneli"
    readonly property string tabFindings: "Sorunlar ve Bulgular"
    readonly property string tabArchive: "Arşivleme ve Dağıtım"
    readonly property string tabCleanup: "Proje Temizliği"
    readonly property string tabSettings: "Ayarlar ve Eşikler"

    // Genel Eylemler & Durumlar
    readonly property string openProject: "Proje Dizini Aç"
    readonly property string reAnalyze: "Yeniden Analiz Et"
    readonly property string exportHtmlReport: "HTML Raporu Al"
    readonly property string exportAuditReport: "Markdown Denetim Raporu Al"
    readonly property string selectFolder: "Dizin Seçin"
    readonly property string cancel: "İptal"
    readonly property string apply: "Uygula"
    readonly property string close: "Kapat"
    readonly property string ready: "Hazır"
    readonly property string analyzing: "Analiz Ediliyor..."
    readonly property string completed: "Tamamlandı"
    readonly property string noProjectSelected: "Henüz bir proje seçilmedi"
    readonly property string selectProjectPrompt: "Analize başlamak için lütfen bir proje dizini seçin"

    // Gösterge Paneli
    readonly property string healthScore: "Proje Sağlık Skoru"
    readonly property string totalFiles: "Toplam Dosya"
    readonly property string projectSize: "Proje Boyutu"
    readonly property string totalFolders: "Klasör Sayısı"
    readonly property string detectedIssues: "Tespit Edilen Sorunlar"
    readonly property string potentialSavings: "Tahmini Alan Tasarrufu"
    readonly property string fileDistribution: "Dosya Türü Dağılımı"
    readonly property string languageDistribution: "Programlama Dilleri Dağılımı"
    readonly property string recommendations: "Öncelikli Sistem Önerileri"
    readonly property string analysisIntegrity: "Analiz Bütünlüğü ve Kapsamı"
    readonly property string skippedFiles: "Atlanan Dosyalar"
    readonly property string gitignoreIgnored: "Gitignore Dışı Kalanlar"
    readonly property string failedAnalyzers: "Hata Veren Analizörler"

    // Bulgular
    readonly property string allFindings: "Tüm Bulgular"
    readonly property string criticalIssues: "Kritik Sorunlar"
    readonly property string highIssues: "Yüksek Öncelik"
    readonly property string mediumWarnings: "Orta Öncelik (Uyarı)"
    readonly property string suggestions: "Düşük / İyileştirme"
    readonly property string searchPlaceholder: "Bulgu, kural veya dosya adı ara..."
    readonly property string noIssuesFound: "Tebrikler. Belirtilen kriterde hiçbir yapısal sorun bulunamadı."

    // Arşivleme
    readonly property string archiveTitle: "Proje Arşivleme ve Dağıtım"
    readonly property string archiveSubtitle: "Gitignore kurallarına ve sıkıştırma profillerine uygun temiz arşiv üretir."
    readonly property string compressionProfile: "Sıkıştırma Profili"
    readonly property string createZipArchive: "Zip Arşivi Oluştur"
    readonly property string createCleanCopy: "Temiz Klasör Kopyası Oluştur"
    readonly property string takeBackup: "Hızlı Proje Yedeği Al"
    readonly property string backupDescription: "Yeniden üretilebilir klasörler hariç tutularak doğrudan ~/.gitclean_backups dizinine yedekler."
    readonly property string archiveProgress: "Arşivleme İlerlemesi"
    readonly property string archiveResult: "İşlem Sonucu"

    // Temizlik
    readonly property string cleanupTitle: "Güvenli Proje Temizliği"
    readonly property string cleanupSubtitle: "Gereksiz önbellek, geçici dosya ve logları Geri Dönüşüm Kutusu'na taşır."
    readonly property string previewCleanup: "Önizleme (Dry-Run)"
    readonly property string runCleanup: "Temizliği Başlat"
    readonly property string cleanupNotice: "Dikkat: Dosyalar kalıcı olarak silinmez, sisteminizin Geri Dönüşüm Kutusu'na taşınır."

    // Ayarlar
    readonly property string settingsTitle: "Yapılandırma ve Analiz Eşikleri"
    readonly property string respectGitignore: ".gitignore Kurallarını Uygula"
    readonly property string activeAnalyzers: "Aktif Analizörler"
    readonly property string thresholdSettings: "Kalite Eşikleri"
    readonly property string themeToggle: "Tema Değiştir (Açık / Koyu)"
}
