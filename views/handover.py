"""분석 로그 · 인수인계 (기획서 §4.9) — AI 결과 / 판독관 판단 / 지휘관 조치를 분리 조회한다.

교대 근무 시 당일 분석 요약·재확인 필요 대상을 확인하고, 필터·검색·CSV Export를 제공한다.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from common import (DATA_DIR, change_totals, load_analysis_log, load_commander_actions,
                    load_opinions, render_header, render_sidebar_tree, review_needed_count)

LOG_COLUMN_ORDER = ["일시", "센서", "분석유형", "계급", "이름", "평균신뢰도", "내용", "상태", "파일명"]
LOG_COL_CFG = {
    "일시": st.column_config.DatetimeColumn("일시", format="YYYY-MM-DD HH:mm"),
    "평균신뢰도": st.column_config.ProgressColumn("신뢰도", min_value=0.0, max_value=1.0, format="percent"),
}


def _ai_log_tab() -> None:
    log = load_analysis_log()
    today = pd.Timestamp.today().normalize()
    day = log["일시"].dt.normalize()

    f1, f2, f3 = st.columns([1.4, 1.4, 1])
    with f1:
        types = st.multiselect("분석 유형", ["지역탐지", "객체식별"], default=["지역탐지", "객체식별"])
    with f2:
        period = st.date_input("기간", value=(today.date() - pd.Timedelta(days=7), today.date()))
    with f3:
        keyword = st.text_input("검색", placeholder="파일명·내용")

    filtered = log[log["분석유형"].isin(types)]
    if isinstance(period, tuple) and len(period) == 2:
        filtered = filtered[(day >= pd.Timestamp(period[0])) & (day <= pd.Timestamp(period[1]))]
    if keyword:
        mask = filtered["파일명"].str.contains(keyword, case=False, na=False) | \
            filtered["내용"].astype(str).str.contains(keyword, case=False, na=False)
        filtered = filtered[mask]

    tab_all, tab_sar, tab_eo = st.tabs(["전체", "SAR", "EO"])
    for tab, subset in ((tab_all, filtered),
                        (tab_sar, filtered[filtered["센서"] == "SAR"]),
                        (tab_eo, filtered[filtered["센서"] == "EO"])):
        with tab:
            st.dataframe(subset, hide_index=True, width="stretch",
                         column_config=LOG_COL_CFG, column_order=LOG_COLUMN_ORDER)

    b1, b2, _ = st.columns([1, 1, 2])
    with b1:
        if st.button("💾 로그 저장", width="stretch"):
            export_dir = DATA_DIR / "exports"
            export_dir.mkdir(exist_ok=True)
            path = export_dir / f"analysis_log_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
            filtered.to_csv(path, index=False, encoding="utf-8-sig")
            st.toast(f"로그가 저장되었습니다: data/exports/{path.name}", icon="💾")
    with b2:
        st.download_button(
            "⬇️ Export CSV", filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"analysis_log_{today:%Y%m%d}.csv", mime="text/csv", width="stretch")


def _opinions_tab() -> None:
    op = load_opinions()
    st.caption(f"판독관 판단 기록 {len(op)}건 — 분석 결과에 대한 판독관 의견(정상/오탐/미탐/분류오류)")
    st.dataframe(op.iloc[::-1], hide_index=True, width="stretch")
    if len(op):
        st.download_button("⬇️ 판독관 의견 CSV", op.to_csv(index=False).encode("utf-8-sig"),
                           file_name="opinions.csv", mime="text/csv")


def _commander_tab() -> None:
    ca = load_commander_actions()
    st.caption(f"지휘관 조치 기록 {len(ca)}건 — 지속 감시·추가 정찰 요청·대응 준비·상급 보고")
    st.dataframe(ca.iloc[::-1], hide_index=True, width="stretch")
    if len(ca):
        st.download_button("⬇️ 지휘관 조치 CSV", ca.to_csv(index=False).encode("utf-8-sig"),
                           file_name="commander_actions.csv", mime="text/csv")


def handover_page() -> None:
    render_header("분석 로그 · 인수인계", "AI 결과 / 판독관 판단 / 지휘관 조치 기록을 분리 조회합니다.")
    render_sidebar_tree()

    log = load_analysis_log()
    today = pd.Timestamp.today().normalize()
    today_n = int((log["일시"].dt.normalize() == today).sum())
    changes = change_totals()

    st.markdown("##### 🧾 인수인계 요약")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("오늘 분석", f"{today_n}건", border=True)
    k2.metric("재확인 필요", f"{review_needed_count()}건", border=True)
    k3.metric("신규 등장", f"{changes['신규']}건", border=True)
    k4.metric("소실 객체", f"{changes['소실']}건", border=True)
    k5.metric("판독 완료", f"{len(load_opinions())}건", border=True)
    if st.checkbox("교대 인수인계 확인 완료로 표시"):
        st.success("인수인계 확인이 완료 처리되었습니다. 다음 근무자에게 분석 연속성이 전달됩니다.", icon="✅")
    st.divider()

    t_ai, t_op, t_cmd = st.tabs(["📋 분석 로그 (AI 결과)", "🎖️ 판독관 의견", "⭐ 지휘관 조치"])
    with t_ai:
        _ai_log_tab()
    with t_op:
        _opinions_tab()
    with t_cmd:
        _commander_tab()
