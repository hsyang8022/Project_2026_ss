"""시간대별 변화 분석 (기획서 §4.7) — 동일 구역 이전/현재 시점 영상을 4분할 비교하고
bbox 중심좌표 거리 기반 매칭으로 신규/소실/유지/위치·클래스 변화/불확실 상태를 표시한다.

주의: 실시간 추적이 아니라 촬영 시점 기준 변화 분석이며, 동일 객체 여부는 후보 매칭으로 표시한다.
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

from common import (CHANGE_MEMO_COLS, CHANGE_MEMO_PATH, append_csv_row, current_user,
                    img_path, load_detections, match_detections, scene_meta, scene_pairs,
                    user_badge)

STATE_BADGE = {
    "신규": "🟢 신규", "소실": "🔴 소실", "위치 변화": "🟠 위치 변화",
    "클래스 변화": "🟣 클래스 변화", "불확실": "⚪ 불확실", "유지": "🔵 유지",
}
IMG_WIDTH = 360  # 4분할이 1080p 한 화면에 들어가는 고정폭(px)


def change_analysis_page() -> None:
    # 제목·센서·구역(시점쌍)·회원정보를 한 행에 통합
    t_col, c_sensor, c_pair, u_col = st.columns([1.7, 1.2, 2.2, 0.9], vertical_alignment="center")
    t_col.markdown("#### ⏱️ 시간대별 변화 분석")
    with c_sensor:
        sensor = st.radio("센서", ["SAR", "EO"], horizontal=True, label_visibility="collapsed")
    pairs = {k: v for k, v in scene_pairs(sensor).items() if len(v) >= 2}
    with c_pair:
        if not pairs:
            st.warning("2시점 이상 수집된 구역이 없습니다.")
            return
        pair_key = st.selectbox("구역 (수집일)", list(pairs), label_visibility="collapsed")
    with u_col:
        user_badge()

    scenes = pairs[pair_key]
    prev_s, curr_s = scenes[0], scenes[-1]
    pm, cm = scene_meta(prev_s), scene_meta(curr_s)
    st.caption(f"📄 {pm['구역']} · {pm['수집일']} · 이전 {pm['시각']} → 현재 {cm['시각']} "
               "· 실시간 추적이 아닌 촬영 시점 기준 변화 분석입니다.")

    det = load_detections()
    prev = det[(det["센서"] == sensor) & (det["파일명"] == prev_s)]
    curr = det[(det["센서"] == sensor) & (det["파일명"] == curr_s)]
    changes = match_detections(prev, curr)

    # ── 4분할: (이전 원본 | 현재 원본) / (이전 탐지 | 현재 탐지) ──
    r1c1, r1c2 = st.columns(2, gap="small")
    r1c1.image(str(img_path(sensor, "원본", prev_s)), width=IMG_WIDTH, caption=f"이전 시점 원본 ({pm['시각']})")
    r1c2.image(str(img_path(sensor, "원본", curr_s)), width=IMG_WIDTH, caption=f"현재 시점 원본 ({cm['시각']})")
    r2c1, r2c2 = st.columns(2, gap="small")
    r2c1.image(str(img_path(sensor, "객체식별", prev_s)), width=IMG_WIDTH, caption="이전 시점 탐지 결과")
    r2c2.image(str(img_path(sensor, "객체식별", curr_s)), width=IMG_WIDTH, caption="현재 시점 탐지 결과")

    # ── 변화 요약 KPI + 변화 테이블 + 메모 ──
    n_new = int((changes["상태"] == "신규").sum())
    n_lost = int((changes["상태"] == "소실").sum())
    n_move = int((changes["상태"].isin(["위치 변화", "클래스 변화"])).sum())
    n_keep = int((changes["상태"] == "유지").sum())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🟢 신규 등장", f"{n_new}건", border=True)
    k2.metric("🔴 소실", f"{n_lost}건", border=True)
    k3.metric("🟠 위치·클래스 변화", f"{n_move}건", border=True)
    k4.metric("🔵 유지", f"{n_keep}건", border=True)

    c_tbl, c_memo = st.columns([1.6, 1], gap="medium")
    with c_tbl:
        st.markdown("##### 📋 변화 분석 결과")
        disp = changes.copy()
        disp["상태"] = disp["상태"].map(lambda s: STATE_BADGE.get(s, s))
        st.dataframe(disp, hide_index=True, width="stretch",
                     column_config={"신뢰도": st.column_config.ProgressColumn(
                         "신뢰도", min_value=0.0, max_value=1.0, format="percent")})
        st.caption("⚠️ 변화가 큰 객체(신규·소실·위치 변화)는 재확인 필요 대상으로 우선 검토하세요.")
    with c_memo:
        st.markdown("##### ✍️ 판독관 메모")
        with st.form("change_memo", clear_on_submit=True):
            memo = st.text_area("변화 분석 메모", height=150, max_chars=1000,
                                placeholder="예: B구역 신규 차량 2대 — 추가 정찰 요청 검토 필요")
            saved = st.form_submit_button("변화 분석 저장", type="primary", width="stretch")
        if saved:
            u = current_user()
            append_csv_row(CHANGE_MEMO_PATH, {
                "작성시간": f"{dt.datetime.now():%Y-%m-%d %H:%M}",
                "작성자": f"{u['rank']} {u['name']}" if u else "-",
                "센서": sensor, "구역": pm["구역"],
                "이전시점": f"{pm['수집일']} {pm['시각']}", "현재시점": f"{cm['수집일']} {cm['시각']}",
                "신규": n_new, "소실": n_lost, "위치변화": n_move, "메모": memo,
            }, CHANGE_MEMO_COLS)
            st.toast("변화 분석 결과가 저장되었습니다.", icon="💾")
