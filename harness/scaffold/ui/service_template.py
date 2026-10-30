"""서비스 계층 템플릿 — 입력 검증, 실행 폴더, 설정 기록, 안전한 내보내기.

복사: cp harness/scaffold/ui/service_template.py src/service.py
구조: core(계산, src/) ← service(이 파일) ← ui(화면). 화면은 이 파일만 호출한다.
실행 폴더: runs/<run_id>/ 에 input.csv, meta.json, config.json, status.json, outputs/*.csv 를 남긴다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import uuid
from pathlib import Path
from typing import Callable

import pandas as pd

RUNS_DIR = Path("runs")
MAX_MB = 50
ALLOWED_EXT = {".csv"}
FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")


# ---------------------------------------------------------------- 입력 검증
def validate_upload(name: str, data: bytes, required_cols: list[str],
                    max_mb: float = MAX_MB, allowed_ext: set[str] = ALLOWED_EXT):
    """(DataFrame 또는 None, 오류 목록). 오류가 있으면 DataFrame 은 None."""
    errors = []
    ext = Path(name).suffix.lower()
    if ext not in allowed_ext:
        errors.append(f"허용하지 않는 형식: {ext or '(없음)'} (허용: {', '.join(sorted(allowed_ext))})")
    if len(data) > max_mb * 1024 * 1024:
        errors.append(f"파일이 너무 큼: {len(data) / 1024 / 1024:.1f}MB (최대 {max_mb}MB)")
    if errors:
        return None, errors
    try:
        df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except Exception as e:  # noqa: BLE001
        return None, [f"CSV 를 읽을 수 없음: {type(e).__name__}"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        errors.append(f"필수 열 없음: {', '.join(missing)}")
    if df.empty:
        errors.append("데이터 행이 없음")
    return (None, errors) if errors else (df, [])


# ---------------------------------------------------------------- 실행 폴더
def new_run(base: Path = RUNS_DIR) -> Path:
    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    run_dir = base / run_id
    (run_dir / "outputs").mkdir(parents=True)
    return run_dir


def save_input(run_dir: Path, data: bytes, original_name: str) -> dict:
    """업로드 원본은 서버가 정한 이름으로 저장하고, 원래 이름은 메타데이터로만 남긴다."""
    (run_dir / "input.csv").write_bytes(data)
    meta = {
        "original_name": re.sub(r"[^\w.\- ]", "_", Path(original_name).name)[:120],
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "saved_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(run_dir / "meta.json", meta)
    return meta


def load_config(path: str | Path) -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def execute(run_dir: Path, df: pd.DataFrame, config: dict,
            core: Callable[[pd.DataFrame, dict], dict[str, pd.DataFrame]]) -> dict:
    """core(df, config) -> {표 이름: DataFrame}. 결과와 상태를 실행 폴더에 남긴다."""
    _write_json(run_dir / "config.json", config)
    try:
        tables = core(df, config)
        for name, table in tables.items():
            table.to_csv(run_dir / "outputs" / f"{_slug(name)}.csv", index=False, encoding="utf-8-sig")
        status = {"ok": True, "tables": sorted(_slug(n) for n in tables)}
    except Exception as e:  # noqa: BLE001
        status = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    status["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
    _write_json(run_dir / "status.json", status)
    return status


def list_runs(base: Path = RUNS_DIR) -> list[dict]:
    """최근 실행부터. 각 항목: run_id, ok, original_name, finished_at."""
    rows = []
    for d in sorted(base.glob("*/"), reverse=True):
        status = load_config(d / "status.json")
        meta = load_config(d / "meta.json")
        if status:
            rows.append({"run_id": d.name, "ok": status.get("ok"), "original_name": meta.get("original_name"),
                         "finished_at": status.get("finished_at")})
    return rows


def read_output(run_id: str, table: str, base: Path = RUNS_DIR) -> pd.DataFrame:
    path = base / _slug(run_id) / "outputs" / f"{_slug(table)}.csv"
    return pd.read_csv(path, encoding="utf-8-sig")


# ---------------------------------------------------------------- 내보내기
def safe_for_spreadsheet(df: pd.DataFrame) -> pd.DataFrame:
    """Excel 에서 수식으로 실행될 수 있는 문자열 셀 앞에 ' 를 붙인다 (CSV 인젝션 방지)."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].map(lambda v: "'" + v if isinstance(v, str) and v.startswith(FORMULA_PREFIX) else v)
    return out


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return safe_for_spreadsheet(df).to_csv(index=False).encode("utf-8-sig")


# ---------------------------------------------------------------- 내부
def _slug(name: str) -> str:
    s = re.sub(r"[^\w\-]", "_", str(name))
    if not s:
        raise ValueError("빈 이름")
    return s


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
