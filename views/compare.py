"""비교 분석 페이지 — 4사분면 SAR/EO 원본·분석 영상 비교, 메모(500자), 레이아웃 초기화, 비교 저장.

23인치(1920×1080) 모니터 100% 배율에서 스크롤 없이 전체 기능이 보이도록
제목·버튼을 한 행으로 통합하고, 각 사분면은 이미지(좌) | 선택·메모(우) 구조로 압축했다.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from common import (DATA_DIR, append_csv_row, current_user, img_path,
                    list_scenes, render_sidebar_tree, user_badge)

SOURCES = {
    "SAR 원본": ("SAR", "원본"),
    "SAR 분석(객체식별)": ("SAR", "객체식별"),
    "EO 원본": ("EO", "원본"),
    "EO 분석(객체식별)": ("EO", "객체식별"),
}

COMPARISON_PATH = DATA_DIR / "comparisons.csv"
COMPARISON_COLS = ["저장시각", "작성자"] + [
    f"Q{q}_{field}" for q in range(1, 5) for field in ("영상", "파일", "메모")]

IMG_WIDTH = 500  # 1080p 100% 배율에서 2행이 한 화면에 들어가는 고정폭(px)


def _reset_layout() -> None:
    for key in [k for k in st.session_state if k.startswith("q")]:
        del st.session_state[key]


def _history_popover() -> None:
    with st.popover("📑 이력", width="stretch"):
        if COMPARISON_PATH.exists():
            saved = pd.read_csv(COMPARISON_PATH, encoding="utf-8-sig")
            st.caption(f"총 {len(saved)}건")
            st.dataframe(saved.iloc[::-1], hide_index=True, width="stretch")
            st.download_button(
                "⬇️ 비교 이력 CSV 내보내기",
                saved.to_csv(index=False).encode("utf-8-sig"),
                file_name="comparisons.csv", mime="text/csv",
            )
        else:
            st.caption("저장된 비교 이력이 없습니다.")


def compare_page() -> None:
    render_sidebar_tree()

    # 제목·안내·버튼·회원정보를 한 행에 통합 (수직 공간 절약)
    t_col, cap_col, b1, b2, b3, u_col = st.columns(
        [1.3, 2.2, 1, 1, 0.6, 0.9], vertical_alignment="center")
    t_col.markdown("#### 🆚 비교 분석")
    cap_col.caption("📝 메모는 세션 동안만 유지됩니다. 기록이 필요하면 '비교 저장'을 사용하세요.")
    reset_clicked = b1.button("🔄 레이아웃 초기화", width="stretch")
    save_clicked = b2.button("💾 비교 저장", type="primary", width="stretch")
    with b3:
        _history_popover()
    with u_col:
        user_badge()

    if reset_clicked:
        _reset_layout()
        st.rerun()

    source_names = list(SOURCES)
    quadrants: list[dict] = []
    for row in range(2):
        cols = st.columns(2, gap="small")
        for col_idx in range(2):
            q = row * 2 + col_idx
            with cols[col_idx], st.container(border=True):
                c_img, c_ctl = st.columns([1.5, 1], gap="small")
                with c_ctl:
                    src = st.selectbox("영상 종류", source_names, index=q, key=f"q{q}_src",
                                       label_visibility="collapsed")
                    sensor, folder = SOURCES[src]
                    scene = st.selectbox("파일", list_scenes(sensor), key=f"q{q}_file_{sensor}",
                                         label_visibility="collapsed")
                    memo = st.text_area(
                        "메모", key=f"q{q}_memo", height=110, max_chars=500,
                        placeholder="메모를 입력하세요.",
                        label_visibility="collapsed")
                c_img.image(str(img_path(sensor, folder, scene)), width=IMG_WIDTH)
                quadrants.append({"영상": src, "파일": f"{scene}.png", "메모": memo or ""})

    if save_clicked:
        u = current_user()
        row_data: dict = {
            "저장시각": f"{dt.datetime.now():%Y-%m-%d %H:%M}",
            "작성자": f"{u['rank']} {u['name']}" if u else "-",
        }
        for i, quad in enumerate(quadrants, 1):
            for field, value in quad.items():
                row_data[f"Q{i}_{field}"] = value
        append_csv_row(COMPARISON_PATH, row_data, COMPARISON_COLS)
        st.toast("비교 결과가 저장되었습니다.", icon="💾")
