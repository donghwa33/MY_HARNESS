"""service_template 자체 테스트: 업로드 검증, 실행 폴더, CSV 인젝션 방지."""
import json

import pandas as pd

from harness.scaffold.ui import service_template as svc


def test_validate_upload_ok_and_errors():
    df, errs = svc.validate_upload("a.csv", b"lot,y\nL1,0.9\n", ["lot", "y"])
    assert errs == [] and len(df) == 1
    _, errs = svc.validate_upload("a.xlsx", b"x", ["lot"])
    assert "허용하지 않는 형식" in errs[0]
    _, errs = svc.validate_upload("a.csv", b"lot\nL1\n", ["lot", "y"])
    assert "필수 열 없음: y" in errs[0]
    _, errs = svc.validate_upload("a.csv", b"x" * 2048, [], max_mb=0.001)
    assert "너무 큼" in errs[0]


def test_run_folder_records_everything(tmp_path):
    run_dir = svc.new_run(tmp_path)
    meta = svc.save_input(run_dir, b"lot,y\nL1,0.9\n", "../../evil name?.csv")
    assert "/" not in meta["original_name"] and (run_dir / "input.csv").exists()
    df = pd.DataFrame({"lot": ["L1"], "y": ["0.9"]})
    status = svc.execute(run_dir, df, {"th": 1}, lambda d, c: {"summary": d})
    assert status["ok"] and (run_dir / "outputs" / "summary.csv").exists()
    assert json.loads((run_dir / "config.json").read_text(encoding="utf-8")) == {"th": 1}
    assert svc.list_runs(tmp_path)[0]["run_id"] == run_dir.name
    assert len(svc.read_output(run_dir.name, "summary", tmp_path)) == 1


def test_execute_records_failure(tmp_path):
    run_dir = svc.new_run(tmp_path)
    status = svc.execute(run_dir, pd.DataFrame(), {}, lambda d, c: 1 / 0)
    assert not status["ok"] and "ZeroDivisionError" in status["error"]


def test_csv_injection_escaped():
    df = pd.DataFrame({"a": ["=1+1", "@SUM(A1)", "ok", "-2"], "n": [1, 2, 3, -4]})
    out = pd.read_csv(__import__("io").BytesIO(svc.to_csv_bytes(df)), encoding="utf-8-sig", dtype=str)
    assert list(out["a"]) == ["'=1+1", "'@SUM(A1)", "ok", "'-2"]
    assert list(out["n"]) == ["1", "2", "3", "-4"]   # 숫자 열은 그대로


def test_slug_neutralizes_paths():
    import pytest
    assert "/" not in svc._slug("../../etc/passwd") and "." not in svc._slug("../x")
    with pytest.raises(ValueError):
        svc._slug("")
