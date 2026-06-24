"""메인 화면 / 빠른 분석 — 6종 KPI 카드, 일일 업무 체크리스트, 오늘의 분석 건수 도넛, 최근 분석 미리보기.

전체 분석 로그 필터·조회·Export는 '분석 로그·인수인계' 페이지로 이관했다 (기획서 §4.9).
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from common import (change_totals, load_analysis_log, load_detections, load_opinions,
                    render_header, render_sidebar_tree, review_needed_count)

STATUS_ORDER = ["완료", "진행중", "대기"]
STATUS_COLORS = ["#1f6fde", "#f5a623", "#b8c4d6"]

LOG_COLUMN_ORDER = ["일시", "센서", "분석유형", "계급", "이름", "평균신뢰도", "내용", "상태", "파일명"]


def _donut_chart(counts: pd.DataFrame, total: int) -> alt.LayerChart:
    base = alt.Chart(counts).encode(
        theta=alt.Theta("건수:Q"),
        color=alt.Color(
            "상태:N",
            scale=alt.Scale(domain=STATUS_ORDER, range=STATUS_COLORS),
            legend=alt.Legend(title=None, orient="right", labelFontSize=13),
        ),
        tooltip=["상태:N", "건수:Q"],
    )
    donut = base.mark_arc(innerRadius=62, outerRadius=92)
    center = alt.Chart(pd.DataFrame({"라벨": [f"{total}건"]})).mark_text(
        size=30, fontWeight="bold", color="#1c2b41"
    ).encode(text="라벨:N")
    return (donut + center).properties(height=240)


def home_page() -> None:
    render_header("메인 대시보드 · 빠른 분석", "당일 분석 현황과 재확인 필요 대상을 한눈에 확인합니다.")
    render_sidebar_tree()

    log = load_analysis_log()
    today = pd.Timestamp.today().normalize()
    day = log["일시"].dt.normalize()
    today_df = log[day == today]
    yest_df = log[day == today - pd.Timedelta(days=1)]

    det = load_detections()
    changes = change_totals()
    n_opinion = len(load_opinions())

    # ── 6종 요약 KPI 카드 (기획서 §4.2) ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("오늘 분석 건수", f"{len(today_df)}건",
              delta=f"{len(today_df) - len(yest_df):+d}건 (전일 대비)", border=True)
    c2.metric("탐지 객체 수", f"{len(det)}건", border=True,
              help="AI가 탐지한 전체 객체 후보 수입니다.")
    c3.metric("재확인 필요", f"{review_needed_count()}건", border=True,
              help="신뢰도 저하 등으로 재검토가 필요한 객체 후보 수입니다.")
    c4.metric("신규 등장", f"{changes['신규']}건", border=True,
              help="이전 시점 대비 새롭게 탐지된 객체 후보 수입니다.")
    c5.metric("소실 객체", f"{changes['소실']}건", border=True,
              help="이전 시점에는 있었으나 현재 탐지되지 않은 객체 수입니다.")
    c6.metric("판독 완료", f"{n_opinion}건", border=True,
              help="판독관 의견이 저장된 분석 건수입니다.")

    left, right = st.columns([1, 1.4], gap="large")

    with left:
        with st.container(border=True):
            st.markdown("##### ✅ 일일 업무 체크리스트")
            n_total, n_done = len(log), (log["상태"] == "완료").sum()
            n_wait = (log["상태"] == "대기").sum()
            items = [
                ("수집 데이터 확인", f"전체 {log['파일명'].nunique()}건 수집"),
                ("미분석 데이터 확인", f"대기 {n_wait}건"),
                ("분석 수행", f"완료 {n_done} / {n_total}건"),
                ("판독 의견 입력 및 저장", f"의견 {n_opinion}건 저장됨"),
                ("변화 분석 / 인수인계", f"신규 {changes['신규']} · 소실 {changes['소실']}건"),
            ]
            done = 0
            for i, (title, count_caption) in enumerate(items):
                done += st.checkbox(f"{title} — :gray[{count_caption}]", key=f"chk_{i}")
            st.progress(done / len(items), text=f"진행률 {done}/{len(items)}")

    with right:
        with st.container(border=True):
            st.markdown("##### 🍩 오늘의 분석 건수")
            counts = (today_df["상태"].value_counts()
                      .reindex(STATUS_ORDER, fill_value=0)
                      .rename_axis("상태").reset_index(name="건수"))
            st.altair_chart(_donut_chart(counts, len(today_df)), width="stretch")
            st.caption(f"기준: {today:%Y-%m-%d}")

    st.markdown("##### 📋 최근 분석 로그 (최근 8건)")
    recent = log.sort_values("일시", ascending=False).head(8)
    st.dataframe(
        recent, hide_index=True, width="stretch", column_order=LOG_COLUMN_ORDER,
        column_config={
            "일시": st.column_config.DatetimeColumn("일시", format="YYYY-MM-DD HH:mm"),
            "평균신뢰도": st.column_config.ProgressColumn("신뢰도", min_value=0.0, max_value=1.0, format="percent"),
        })
    st.caption("🔎 전체 로그 필터·검색·CSV Export와 인수인계는 상단 '분석 로그·인수인계' 페이지에서 제공합니다.")
