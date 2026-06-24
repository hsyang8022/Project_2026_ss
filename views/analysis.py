"""SAR / EO 분석 페이지 — 지역 탐지·객체 식별 탭, 분석 결과 테이블, 판독관 의견 저장."""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from common import (OPINION_COLS, OPINION_PATH, TARGET_TYPE_GUIDE, append_csv_row,
                    classify_target_type, detection_overlay, img_path, load_detections,
                    load_opinions, load_regions, render_header, scene_meta,
                    sidebar_scene_picker)

VERDICTS = ["정상 탐지", "오탐 포함", "미탐 의심", "분류 오류"]

CONF_COL = st.column_config.ProgressColumn("신뢰도", min_value=0.0, max_value=1.0, format="percent")


def _opinion_form(sensor: str, scene: str, meta: dict, sel: pd.DataFrame, tab_key: str) -> None:
    """판독관 의견 입력·저장 폼 — 지역탐지/객체식별 탭 공용."""
    st.markdown("##### ✍️ 판독관 의견 입력 및 저장")
    with st.form(f"opinion_{sensor}_{tab_key}", clear_on_submit=True):
        o1, o2 = st.columns([1, 2])
        with o1:
            verdict = st.selectbox("판독 평가", VERDICTS,
                                   help="오탐·미탐 평가는 모델 재학습 자료로 축적됩니다.")
            summary = st.text_input("결과 요약", placeholder="예: 차량 집결 정황 식별")
        with o2:
            comment = st.text_area("상세 의견", height=120, max_chars=1000,
                                   placeholder="판독 결과에 대한 의견을 입력하세요.")
        submitted = st.form_submit_button("의견 저장", type="primary")

    if submitted:
        conf_range = f"{sel['신뢰도'].min():.2f}~{sel['신뢰도'].max():.2f}" if len(sel) else "—"
        location = (f"{meta['구역']} ({sel['위도'].mean():.4f}, {sel['경도'].mean():.4f})"
                    if len(sel) else meta["구역"])
        append_csv_row(OPINION_PATH, {
            "작성시간": f"{dt.datetime.now():%Y-%m-%d %H:%M}",
            "파일명": f"{scene}.png",
            "센서": sensor,
            "수집일": meta["수집일"],
            "위치": location,
            "평가": verdict,
            "결과 요약": summary,
            "상세 의견": comment,
            "탐지수": len(sel),
            "신뢰도 범위": conf_range,
        }, OPINION_COLS)
        st.toast("판독관 의견이 저장되었습니다.", icon="✅")

    opinions = load_opinions()
    with st.expander(f"📑 저장된 판독관 의견 ({len(opinions)}건)"):
        st.dataframe(opinions, hide_index=True, width="stretch")
        if len(opinions):
            st.download_button(
                "⬇️ 판독관 의견 CSV 내보내기",
                opinions.to_csv(index=False).encode("utf-8-sig"),
                file_name="opinions.csv", mime="text/csv", key=f"dl_op_{sensor}_{tab_key}",
            )


def render_analysis(sensor: str) -> None:
    render_header(f"{sensor} 분석", "지역 탐지 → 객체 식별 순으로 분석 결과를 확인하고 판독관 의견을 기록합니다.")
    scene = sidebar_scene_picker(sensor)
    meta = scene_meta(scene)
    st.caption(f"📄 {scene}.png · 수집일 {meta['수집일']} · {meta['구역']} · 센서 {sensor}")

    det = load_detections()
    det_all = det[(det["센서"] == sensor) & (det["파일명"] == scene)]
    regions = load_regions()
    reg = regions[(regions["센서"] == sensor) & (regions["파일명"] == scene)]

    tab_region, tab_object = st.tabs(["🗺️ 지역 탐지", "🎯 객체 식별"])

    with tab_region:
        c_img, c_tbl = st.columns([1.9, 1], gap="medium")
        with c_img:
            st.markdown(f"**선택 이미지** — {scene}.png")
            st.image(str(img_path(sensor, "지역탐지", scene)), width="stretch",
                     caption="지역 탐지 결과 — 관심 구역(AOI) 오버레이")
            with st.expander("수집 원본 보기"):
                st.image(str(img_path(sensor, "원본", scene)), width="stretch")
        with c_tbl:
            st.markdown("**분석 결과**")
            aoi_rows = [{
                "구분": r["구역ID"], "클래스": "관심구역(AOI)", "신뢰도": r["신뢰도"],
                "위도": r["중심위도"], "경도": r["중심경도"],
            } for _, r in reg.iterrows()]
            cand_rows = [{
                "구분": r["객체ID"], "클래스": r["클래스"], "신뢰도": r["신뢰도"],
                "위도": r["위도"], "경도": r["경도"],
            } for _, r in det_all.iterrows()]
            st.dataframe(pd.DataFrame(aoi_rows + cand_rows), hide_index=True, width="stretch",
                         column_config={"신뢰도": CONF_COL})
            n_aoi = len(reg)
            st.metric("관심 구역 / 후보 표적", f"{n_aoi}개소 / {len(det_all)}건", border=True)
        _opinion_form(sensor, scene, meta, det_all, "region")

    with tab_object:
        thr = st.slider("신뢰도 임계값", 0.0, 1.0, 0.7, 0.05, key=f"thr_{sensor}",
                        help="임계값 이상의 탐지 결과만 영상과 목록에 표시합니다.")
        sel = det_all[det_all["신뢰도"] >= thr]

        c_img, c_tbl = st.columns([1.9, 1], gap="medium")
        with c_img:
            st.image(detection_overlay(sensor, scene, thr), width="stretch",
                     caption=f"객체 식별 결과 — 임계값 {thr:.2f} 이상 {len(sel)}건 표시")
        with c_tbl:
            m1, m2 = st.columns(2)
            m1.metric("탐지 객체", f"{len(sel)}건", border=True)
            m2.metric("최고 신뢰도", f"{sel['신뢰도'].max():.2f}" if len(sel) else "—", border=True)
            st.dataframe(
                sel[["객체ID", "클래스", "신뢰도", "위도", "경도"]],
                hide_index=True, width="stretch",
                column_config={"신뢰도": CONF_COL},
            )
            if len(sel):
                ttype = classify_target_type(sel)
                st.info(f"**표적 후보 유형: {ttype}** — {TARGET_TYPE_GUIDE[ttype]}", icon="🎯")
        _opinion_form(sensor, scene, meta, sel, "object")


def sar_page() -> None:
    render_analysis("SAR")


def eo_page() -> None:
    render_analysis("EO")
