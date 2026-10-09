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
    readonly property string noProjectSelected: "Henüz bir proje seçilmedi"
    readonly property string selectProjectPrompt: "Analize başlamak için lütfen bir proje dizini seçin"

    // Gösterge Paneli
    readonly property string healthScore: "Proje Sağlık Skoru"
    readonly property string totalFiles: "Toplam Dosya"
    readonly property string projectSize: "Proje Boyutu"
    readonly property string totalFolders: "Klasör Sayısı"
    readonly property string detectedIssues: "Tespit Edilen Sorunlar"
    readonly property string fileDistribution: "Dosya Türü Dağılımı"
    readonly property string languageDistribution: "Programlama Dilleri Dağılımı"
    readonly property string recommendations: "Öncelikli Sistem Önerileri"
    readonly property string analysisIntegrity: "Analiz Bütünlüğü ve Kapsamı"
    readonly property string skippedFiles: "Atlanan Dosyalar"
    readonly property string gitignoreIgnored: "Gitignore Dışı Kalanlar"

    // Bulgular
    readonly property string noIssuesFound: "Tebrikler. Belirtilen kriterde hiçbir yapısal sorun bulunamadı."

    // Arşivleme
    readonly property string archiveTitle: "Proje Arşivleme ve Dağıtım"
    readonly property string archiveSubtitle: "Gitignore kurallarına ve sıkıştırma profillerine uygun temiz arşiv üretir."
    readonly property string takeBackup: "Hızlı Proje Yedeği Al"
    readonly property string backupDescription: "Yeniden üretilebilir klasörler hariç tutularak doğrudan ~/.gitclean_backups dizinine yedekler. Fazla otomatik yedekler Geri Dönüşüm Kutusu'na taşınır."
    readonly property string keptBackups: "Saklanan yedek:"

    // Temizlik
    readonly property string cleanupTitle: "Güvenli Proje Temizliği"
    readonly property string cleanupSubtitle: "Gereksiz önbellek, geçici dosya ve logları Geri Dönüşüm Kutusu'na taşır."
    readonly property string cleanupNotice: "Dikkat: Dosyalar kalıcı olarak silinmez, sisteminizin Geri Dönüşüm Kutusu'na taşınır."

    // Ayarlar
    readonly property string respectGitignore: ".gitignore Kurallarını Uygula"
    readonly property string respectGitignoreDesc: "Analiz ve arşivleme işlemlerinde .gitignore dosyasındaki yok sayma kurallarına uyar."
    readonly property string activeAnalyzers: "Aktif Analizörler"
    readonly property string activeAnalyzersDesc: "Proje üzerinde çalıştırılacak statik ve yapısal analiz motorlarını belirleyin."
    readonly property string thresholdSettings: "Kod Kalite ve Karmaşıklık Eşikleri"
    readonly property string thresholdSettingsDesc: "Aşıldığında uyarı veya hata üretilecek sınır değerlerini yapılandırın."
    readonly property string agentTaskExportTitle: "Yapay Zeka (Agent) Görev Dağıtımı"
    readonly property string agentTaskExportDesc: "Bulguları LLM ajanlarının paralel çalışabileceği JSON ve Markdown görev paketlerine dönüştürür."
    readonly property string agentBatchSize: "Ajan Başına Görev Sayısı (Batch Size)"
    readonly property string exportAgentTasksBtn: "Ajan Görevlerini Dışa Aktar"
    readonly property string verifyAgentTasksBtn: "Görev Durumunu Doğrula"
    readonly property string resetDefaultsBtn: "Varsayılanlara Sıfırla"
    readonly property string applySettingsBtn: "Ayarları Kaydet ve Uygula"
}
