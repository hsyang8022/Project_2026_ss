"""메인 화면 / 빠른 분석 (영상판독관) — 일일 업무 체크리스트, 오늘의 분석 건수 도넛,
오늘 분석 대기 영상 + 분석 워크플로우 바로가기.

판독관 수요(오늘 무엇을 분석할지 → 바로 분석 진입)에 맞춰 '오늘 분석 대기 영상' 패널과
SAR/EO 분석·분석 로그 페이지 바로가기를 제공한다. 전체 로그 필터·조회·Export는
'분석 로그·인수인계' 페이지에서 제공한다 (기획서 §4.9).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from common import (change_totals, donut_chart, list_scenes, load_analysis_log,
                    load_opinions, render_header, render_sidebar_tree, scene_meta,
                    scene_status)

STATUS_ORDER = ["완료", "진행중", "대기"]
STATUS_COLORS = ["#1f6fde", "#f5a623", "#b8c4d6"]


def _pending_panel() -> None:
    """오늘 분석 대기 영상 + SAR/EO 분석 페이지 바로가기 (판독관 빠른 분석 진입)."""
    status = scene_status()
    nav = st.session_state.get("nav_pages", {})
    with st.container(border=True):
        st.markdown("##### 🚀 오늘 분석 대기 영상")
        cols = st.columns([1, 1, 0.9], gap="medium")
        for col, sensor in zip(cols[:2], ("SAR", "EO")):
            pending = [s for s in list_scenes(sensor)
                       if status.get(f"{s}.png") != "분석완료"]
            with col:
                if pending:
                    st.markdown(f"**📡 {sensor} · 미분석 {len(pending)}건**"
                                if sensor == "SAR" else f"**🛰️ {sensor} · 미분석 {len(pending)}건**")
                    for s in pending[:4]:
                        m = scene_meta(s)
                        st.caption(f"└ {m['수집일']} · {m['구역']} {m['시각']}")
                    if len(pending) > 4:
                        st.caption(f"… 외 {len(pending) - 4}건")
                else:
                    st.markdown(f"**{sensor}**")
                    st.success("수집 영상 전부 분석 완료", icon="✅")
        with cols[2]:
            st.markdown("**바로가기**")
            if "sar" in nav:
                st.page_link(nav["sar"], label="SAR 분석", icon="📡", width="stretch")
                st.page_link(nav["eo"], label="EO 분석", icon="🛰️", width="stretch")
                st.page_link(nav["log"], label="분석 로그·인수인계", icon="🧾", width="stretch")
            else:
                st.caption("상단 메뉴의 SAR/EO 분석·분석 로그로 이동하세요.")


def home_page() -> None:
    render_header("메인 대시보드 · 빠른 분석", "당일 분석 현황과 재확인 필요 대상을 한눈에 확인합니다.")
    render_sidebar_tree()

    log = load_analysis_log()
    today = pd.Timestamp.today().normalize()
    day = log["일시"].dt.normalize()
    today_df = log[day == today]

    changes = change_totals()
    n_opinion = len(load_opinions())

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
            st.altair_chart(donut_chart(counts, len(today_df), STATUS_ORDER, STATUS_COLORS),
                            width="stretch")
            st.caption(f"기준: {today:%Y-%m-%d}")

    _pending_panel()
