"""Streamlit UI 템플릿 — 화면은 service 를 호출하고, 계산은 core 에서 한다.

복사: cp harness/scaffold/ui/streamlit_app_template.py ui/app.py
      cp harness/scaffold/ui/service_template.py src/service.py
실행: bash ui/run.sh   (Windows 사용자 PC: ui\\run.cmd)
고칠 곳: REQUIRED_COLS, CONFIG_PATH, run_core, SUMMARY_TABLE, RESULT_SECTIONS
미리보기 환경에서 업로드가 403 으로 실패하면 run.sh 에 --server.enableXsrfProtection false 를 추가한다.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import service  # noqa: E402

TITLE = "분석 도구"
REQUIRED_COLS: list[str] = []            # 업로드 파일의 필수 열
CONFIG_PATH = "config/settings.json"     # 기준값 등 설정 (없으면 빈 설정)
SUMMARY_TABLE = "summary"                # 실행 후 먼저 보여줄 표 이름
TABLE_DIR = Path("outputs/tables")       # 기존 분석 결과 표
RESULT_SECTIONS = []                     # [(제목, 표 이름, 그림 경로 또는 None)]


def run_core(df: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]:
    """core 함수를 호출하는 자리. 예: from src.analyze import weekly; return weekly(df, config)"""
    return {"summary": pd.DataFrame({"rows": [len(df)], "columns": [len(df.columns)]})}


def show(df: pd.DataFrame) -> None:
    try:
        st.dataframe(df, width="stretch")
    except Exception:  # noqa: BLE001  (구버전 Streamlit)
        st.dataframe(df, use_container_width=True)


@st.cache_data
def read_table(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


st.set_page_config(page_title=TITLE, layout="wide")
st.title(TITLE)
st.session_state.setdefault("run_id", None)
tab_run, tab_history, tab_results = st.tabs(["실행", "이력", "분석 결과"])

with tab_run:
    up = st.file_uploader("CSV 업로드", type=["csv"])
    config = service.load_config(CONFIG_PATH)
    with st.expander("설정", expanded=False):
        for key, value in config.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                config[key] = st.number_input(key, value=value)
    if up is None:
        st.info("CSV 파일을 올리면 형식을 확인한 뒤 실행할 수 있습니다.")
    else:
        data = up.getvalue()
        df, errors = service.validate_upload(up.name, data, REQUIRED_COLS)
        if errors:
            st.error("파일을 확인해 주세요.\n\n" + "\n".join(f"- {e}" for e in errors))
        else:
            st.success(f"형식 확인 완료: {len(df):,}행, {len(df.columns)}열")
            if st.button("실행", type="primary"):
                run_dir = service.new_run()
                service.save_input(run_dir, data, up.name)
                with st.spinner("실행 중"):
                    status = service.execute(run_dir, df, config, run_core)
                if status["ok"]:
                    st.session_state.run_id = run_dir.name
                else:
                    st.error(f"실행 실패: {status['error']}")
    run_id = st.session_state.run_id
    if run_id:
        st.subheader(f"결과 · {run_id}")
        status = service.load_config(service.RUNS_DIR / run_id / "status.json")
        tables = status.get("tables", [])
        if SUMMARY_TABLE in tables:
            show(service.read_output(run_id, SUMMARY_TABLE))
        for name in [t for t in tables if t != SUMMARY_TABLE]:
            with st.expander(name):
                table = service.read_output(run_id, name)
                show(table)
                st.download_button("CSV 다운로드", service.to_csv_bytes(table), f"{name}.csv",
                                   "text/csv", key=f"dl_{run_id}_{name}")

with tab_history:
    runs = service.list_runs()
    if not runs:
        st.info("아직 실행 이력이 없습니다.")
    else:
        show(pd.DataFrame(runs))
        pick = st.selectbox("다시 볼 실행", [r["run_id"] for r in runs if r["ok"]])
        if pick and st.button("이 실행 결과 보기"):
            st.session_state.run_id = pick
            st.rerun()

with tab_results:
    if not RESULT_SECTIONS:
        st.info("표시할 분석 결과가 설정되지 않았습니다.")
    for title, table, figure in RESULT_SECTIONS:
        st.header(title)
        if figure and os.path.exists(figure):
            st.image(figure)
        path = TABLE_DIR / f"{table}.csv"
        if path.exists():
            show(read_table(str(path), path.stat().st_mtime))
            st.caption(f"출처: {path}")
        else:
            st.info(f"표 없음: {path}")
