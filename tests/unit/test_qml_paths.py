from src.qml_ui.viewmodels.paths import local_path


def test_windows_file_url_is_decoded():
    assert local_path("file:///C:/Users/a%20b/%C5%9Fi%C5%9F.zip") == "C:/Users/a b/şiş.zip"


def test_posix_file_url_keeps_leading_slash():
    """Eski `[8:]` kesmesi `/home/x` yolunu göreli `home/x` yapıyordu."""
    assert local_path("file:///home/user/rapor.md") == "/home/user/rapor.md"


def test_unc_url_and_plain_paths():
    assert local_path("file://sunucu/pay/a.zip") == "//sunucu/pay/a.zip"
    assert local_path("C:/proje") == "C:/proje"
    assert local_path("") == ""
