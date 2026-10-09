"""ProjectService: teşhis önbelleği, eşzamanlı isteklerin birleşmesi ve yazma işlemlerinin karşılıklı dışlanması."""
import threading
from pathlib import Path

import pytest

from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.core.base_analyzer import BaseAnalyzer
from src.core.errors import OperationBusyError, ProjectNotSelectedError
from src.doctors.project_doctor import ProjectDoctor
from src.services.project_service import ProjectService


class CountingAnalyzer(BaseAnalyzer):
    """Kaç kez çalıştığını sayar; `gate` verilirse bırakılana kadar bekler (eşzamanlılığı sınamak için)."""
    category = "structure"

    def __init__(self, gate: threading.Event = None):
        super().__init__(10)
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self.entered = threading.Event()
        self.gate = gate

    @property
    def name(self):
        return "Sayaç"

    def analyze(self, index):
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(5)
        self.active -= 1
        return []


def make_service(tmp_path: Path, *analyzers) -> ProjectService:
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    service = ProjectService()
    service.doctor = ProjectDoctor(analyzers=list(analyzers) or [EmptyFolderFinder()], respect_gitignore=False)
    service.set_project(tmp_path)
    return service


def test_diagnose_without_project_raises(tmp_path):
    with pytest.raises(ProjectNotSelectedError):
        ProjectService().diagnose()


def test_dashboard_and_exports_reuse_one_diagnosis(tmp_path):
    counter = CountingAnalyzer()
    service = make_service(tmp_path, counter)
    service.analyze_project()
    service.diagnose()
    service.export_audit_report(tmp_path.parent / "rapor.md")
    assert counter.calls == 1


def test_refresh_rescans_and_cache_is_invalidated_by_settings_and_project_change(tmp_path):
    counter = CountingAnalyzer()
    service = make_service(tmp_path, counter)
    service.diagnose()
    service.diagnose(refresh=True)
    assert counter.calls == 2
    service.doctor = ProjectDoctor(analyzers=[counter], respect_gitignore=False)      # ayarlar uygulandı
    service.diagnose()
    service.set_project(tmp_path)
    service.diagnose()
    assert counter.calls == 4


def test_cleanup_invalidates_cache_but_preview_and_dry_run_do_not(tmp_path):
    counter = CountingAnalyzer()
    service = make_service(tmp_path, counter)
    service.diagnose()
    service.preview_cleanup()
    service.cleanup(dry_run=True)
    service.diagnose()
    assert counter.calls == 1
    service.cleanup_service = type(service.cleanup_service)(trash_func=lambda path: None)
    service.cleanup(dry_run=False)
    service.diagnose()
    assert counter.calls == 2


def test_concurrent_refreshes_share_one_diagnosis_and_never_run_in_parallel(tmp_path):
    """Proje açılınca Dashboard ve Sorunlar aynı anda yeniler: analizörler paylaşıldığı için tek teşhis çalışmalı."""
    gate = threading.Event()
    counter = CountingAnalyzer(gate)
    service = make_service(tmp_path, counter)
    results = []
    first = threading.Thread(target=lambda: results.append(service.diagnose(refresh=True)))
    first.start()
    assert counter.entered.wait(5)
    second = threading.Thread(target=lambda: results.append(service.diagnose(refresh=True)))
    second.start()
    second.join(0.2)
    assert second.is_alive()                             # ilk teşhis bitene kadar bekliyor
    gate.set()
    first.join(5)
    second.join(5)
    assert counter.calls == 2 and counter.max_active == 1
    # ikinci istek ilk teşhis başladıktan sonra geldi: kendi teşhisini yaptı ama paralel değil
    assert len(results) == 2


def test_requests_made_before_a_diagnosis_started_reuse_it(tmp_path):
    gate = threading.Event()
    counter = CountingAnalyzer(gate)
    service = make_service(tmp_path, counter)
    service._diagnose_lock.acquire()                     # iki istek de kilitte beklesin
    results = []
    threads = [threading.Thread(target=lambda: results.append(service.diagnose(refresh=True))) for _ in range(2)]
    for t in threads:
        t.start()
    gate.set()
    service._diagnose_lock.release()
    for t in threads:
        t.join(5)
    assert counter.calls == 1 and results[0] is results[1]


def test_second_write_operation_is_refused_while_first_runs(tmp_path):
    service = make_service(tmp_path)
    started, release = threading.Event(), threading.Event()

    def slow_trash(path):
        started.set()
        release.wait(5)

    (tmp_path / "x.tmp").write_text("t", encoding="utf-8")
    service.cleanup_service = type(service.cleanup_service)(trash_func=slow_trash)
    worker = threading.Thread(target=lambda: service.cleanup(dry_run=False))
    worker.start()
    assert started.wait(5)
    assert service.busy_operation == "temizlik"
    with pytest.raises(OperationBusyError, match="temizlik"):
        service.create_zip(tmp_path.parent / "a.zip")
    release.set()
    worker.join(5)
    assert service.busy_operation == ""
    assert service.create_zip(tmp_path.parent / "a.zip")["success"]


def test_write_during_diagnosis_keeps_stale_result_out_of_cache(tmp_path):
    gate = threading.Event()
    counter = CountingAnalyzer(gate)
    service = make_service(tmp_path, counter)
    worker = threading.Thread(target=service.diagnose)
    worker.start()
    assert counter.entered.wait(5)
    service.copy_project(tmp_path.parent / "kopya")      # teşhis sürerken proje değişti
    gate.set()
    worker.join(5)
    service.diagnose()
    assert counter.calls == 2
