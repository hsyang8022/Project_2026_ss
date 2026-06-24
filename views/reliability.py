"""신뢰성 검토 페이지 — 판독관용 Grad-CAM 집중 영역 검토 + 판독 권고 (수정 액션플랜 §4·§5).

판독관 메인 화면은 Grad-CAM 집중 영역 일치 여부와 판독 권고(신뢰/재확인/수동 판독)를 중심으로 한다.
모델 성능 5종 지표·KPI 비교·SHAP 기여도는 핵심 판독 시나리오가 아닌 '내부 검증 자료'로 분리해
하단 expander로 강등 배치한다.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from common import (CLASSES, img_path, list_scenes, load_detections, load_regions,
                    scene_meta, user_badge, xai_path)

# 판독 권고 규칙 (기획서 §4.5 + 수정 액션플랜 §5 — Grad-CAM 중심)
# (신뢰도 하한, 판독 권고, AI 집중 영역 상태, 대응 가이드, 아이콘)
RECO_RULES = [
    (0.80, "신뢰 가능", "집중 영역이 표적 후보 내부", "원본 영상과 함께 우선 검토", "✅"),
    (0.65, "재확인 필요", "집중 영역이 표적·배경 혼재", "원본·Crop·주변 맥락 재확인", "⚠️"),
    (0.00, "수동 판독 필요", "집중 영역이 표적 외부/분산", "추가 확인 또는 판독 보류", "🔁"),
]

XAI_GUIDE = pd.DataFrame([
    {"Grad-CAM 집중 영역": "표적 후보 박스 내부에 주로 위치", "화면 표시": "AI 집중 영역 일치", "대응 가이드": "원본 영상과 함께 우선 검토"},
    {"Grad-CAM 집중 영역": "표적 후보와 배경에 혼재", "화면 표시": "재검토 필요", "대응 가이드": "원본·Crop·주변 맥락 재확인"},
    {"Grad-CAM 집중 영역": "표적 후보 외부에 주로 위치", "화면 표시": "오탐 의심", "대응 가이드": "보류 또는 제외 검토"},
    {"Grad-CAM 집중 영역": "넓게 분산", "화면 표시": "근거 불명확", "대응 가이드": "추가 확인 또는 판독 보류"},
])

CONF_COL = st.column_config.ProgressColumn("신뢰도", min_value=0.0, max_value=1.0, format="percent")


def _recommend(conf: float) -> tuple[str, str, str, str]:
    for thr, reco, xai, guide, icon in RECO_RULES:
        if conf >= thr:
            return reco, xai, guide, icon
    return RECO_RULES[-1][1], RECO_RULES[-1][2], RECO_RULES[-1][3], RECO_RULES[-1][4]

# 지표: {이름: (이번 모델, KPI 기준, 이전 모델)}
MODELS = {
    "SAR 객체식별 모델 (v2.1)": {
        "sensor": "SAR",
        "지표": {
            "정확도 (Accuracy)": (0.921, 0.90, 0.885),
            "정밀도 (Precision)": (0.931, 0.92, 0.901),
            "재현율 (Recall)": (0.897, 0.90, 0.872),
            "F1-Score": (0.914, 0.91, 0.886),
            "mAP@0.5": (0.913, 0.90, 0.878),
        },
        "클래스AP": {"전차": 0.94, "장갑차": 0.91, "자주포": 0.89, "군용트럭": 0.87},
        "SHAP": {
            "후방산란 강도": 0.34, "객체 형상(종횡비)": 0.22, "그림자 패턴": 0.18,
            "주변 지형 대비": 0.12, "텍스처 균질성": -0.07, "스페클 노이즈 수준": -0.11,
        },
    },
    "EO 객체식별 모델 (v1.4)": {
        "sensor": "EO",
        "지표": {
            "정확도 (Accuracy)": (0.903, 0.89, 0.871),
            "정밀도 (Precision)": (0.905, 0.90, 0.883),
            "재현율 (Recall)": (0.874, 0.89, 0.851),
            "F1-Score": (0.889, 0.89, 0.867),
            "mAP@0.5": (0.892, 0.88, 0.861),
        },
        "클래스AP": {"전투기": 0.93, "수송기": 0.90, "헬기": 0.86, "지상차량": 0.84},
        "SHAP": {
            "객체 색상 대비": 0.31, "객체 형상(종횡비)": 0.24, "그림자 길이": 0.16,
            "주변 도로 인접성": 0.13, "구름/안개 비율": -0.09, "저조도 노이즈": -0.12,
        },
    },
}

HELP = {
    "정확도 (Accuracy)": "전체 판정 중 올바르게 분류한 비율입니다.",
    "정밀도 (Precision)": "탐지한 것 중 실제 표적의 비율. 높을수록 오탐(False Positive)이 적습니다.",
    "재현율 (Recall)": "실제 표적 중 탐지에 성공한 비율. 높을수록 미탐(False Negative)이 적습니다.",
    "F1-Score": "정밀도와 재현율의 조화평균. 두 지표의 균형을 나타냅니다.",
    "mAP@0.5": "IoU 0.5 기준 평균 정밀도(mean Average Precision). 탐지 모델의 종합 성능 지표입니다.",
}

# PALETTE의 클래스 색 순서와 맞춘 Streamlit 마크다운 색상
CLASS_MD_COLORS = ["red", "orange", "violet", "blue"]

IMG_WIDTH = 480  # 1080p 100% 배율에서 우측 패널과 함께 한 화면에 들어가는 고정폭(px)


def _shap_chart(shap: dict[str, float]) -> alt.LayerChart:
    df = pd.DataFrame(
        [{"요소": k, "기여도": v, "방향": "양(+) 기여" if v >= 0 else "음(−) 기여"}
         for k, v in shap.items()])
    y_enc = alt.Y("요소:N", sort="-x", title=None)
    bars = alt.Chart(df).mark_bar().encode(
        y=y_enc,
        x=alt.X("기여도:Q", title="SHAP 값 (기여도)"),
        color=alt.Color("방향:N",
                        scale=alt.Scale(domain=["양(+) 기여", "음(−) 기여"],
                                        range=["#e8336d", "#2e6fdb"]),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["요소:N", "기여도:Q"],
    )
    text_base = alt.Chart(df).encode(y=y_enc, x="기여도:Q",
                                     text=alt.Text("기여도:Q", format="+.2f"))
    pos = text_base.transform_filter(alt.datum.기여도 >= 0).mark_text(align="left", dx=4, color="#444")
    neg = text_base.transform_filter(alt.datum.기여도 < 0).mark_text(align="right", dx=-4, color="#444")
    return (bars + pos + neg).properties(height=190)


def _interpretation(model: dict) -> None:
    """지표·SHAP 데이터 기반 판독관용 해석 요약 — 한 화면 수용을 위해 가로 3분할."""
    st.markdown("##### 🧭 신뢰성 해석 요약 (판독관용)")
    below = [k.split(" ")[0] for k, (v, kpi, _) in model["지표"].items() if v < kpi]
    negatives = [k for k, v in model["SHAP"].items() if v < 0]
    c1, c2, c3 = st.columns(3)
    with c1:
        if below:
            st.warning(f"**모델 신뢰도**: {', '.join(below)} 지표가 KPI 기준에 미달합니다. "
                       "해당 지표 개선을 위한 재학습 검토가 필요합니다.", icon="⚠️")
        else:
            st.success("**모델 신뢰도**: 현재 모델은 전반적으로 안정적인 성능을 보이고 있으며, "
                       "모든 지표가 KPI 기준을 충족합니다.", icon="✅")
    c2.warning(f"**주의 요인**: {', '.join(negatives)} 요소가 성능에 부정적 영향을 줄 수 있습니다.",
               icon="⚠️")
    c3.info("**권장 사항**: 음(−) 기여 요소를 완화하기 위한 전처리 보강과 "
            "해당 조건의 데이터 추가 확보·재학습을 권장합니다.", icon="ℹ️")


def reliability_page() -> None:
    # 제목·모델/영상 선택·회원 정보를 한 행에 통합 (수직 공간 절약)
    t_col, c_model, c_scene, u_col = st.columns(
        [1.7, 1.7, 1.7, 0.9], vertical_alignment="center")
    t_col.markdown("#### 🔬 신뢰성 검토")
    with c_model:
        name = st.selectbox("검토 대상 모델", list(MODELS), label_visibility="collapsed",
                            help="검토 대상 모델")
    model = MODELS[name]
    sensor = model["sensor"]
    with c_scene:
        scene = st.selectbox("대상 영상", list_scenes(sensor), key=f"cam_scene_{sensor}",
                             label_visibility="collapsed", help="대상 영상")
    with u_col:
        user_badge()

    left, right = st.columns([1, 1.5], gap="medium")

    # ── Grad-CAM + 탐지 박스 결합 뷰 (좌) ──
    with left:
        st.image(str(xai_path(sensor, scene, with_boxes=True)), width=IMG_WIDTH)
        legend_md = "  ".join(
            f":{color}[●] {cls}" for cls, color in zip(CLASSES[sensor], CLASS_MD_COLORS))
        st.markdown(f"{legend_md} · AI 집중도: :blue[낮음] → :orange[중간] → :red[높음]")
        meta = scene_meta(scene)
        regions = load_regions()
        reg = regions[(regions["센서"] == sensor) & (regions["파일명"] == scene)]
        coord = (f"{reg.iloc[0]['중심위도']:.4f}° N, {reg.iloc[0]['중심경도']:.4f}° E"
                 if len(reg) else "—")
        st.caption(f"이미지 일시: {meta['수집일']} {meta['시각']} (KST) · 좌표: {coord} · {meta['구역']}")
        with st.expander("원본 영상 비교"):
            c1, c2 = st.columns(2)
            c1.image(str(img_path(sensor, "원본", scene)), width="stretch", caption="수집 원본")
            c2.image(str(xai_path(sensor, scene)), width="stretch", caption="Grad-CAM 히트맵 (박스 미표시)")

    # ── 판독 권고 (우) — Grad-CAM 집중 영역 기반, 판독관 메인 ──
    with right:
        st.markdown("##### 🧭 판독 권고 (선택 영상 객체별)")
        det = load_detections()
        rows = det[(det["센서"] == sensor) & (det["파일명"] == scene)].sort_values("신뢰도", ascending=False)
        reco_rows, counts = [], {"신뢰 가능": 0, "재확인 필요": 0, "수동 판독 필요": 0}
        for _, r in rows.iterrows():
            reco, xai, _guide, icon = _recommend(r["신뢰도"])
            counts[reco] += 1
            reco_rows.append({"객체ID": r["객체ID"], "클래스": r["클래스"], "신뢰도": r["신뢰도"],
                              "판독 권고": f"{icon} {reco}", "AI 집중 영역": xai})
        m1, m2, m3 = st.columns(3)
        m1.metric("✅ 신뢰 가능", f"{counts['신뢰 가능']}건", border=True)
        m2.metric("⚠️ 재확인 필요", f"{counts['재확인 필요']}건", border=True)
        m3.metric("🔁 수동 판독", f"{counts['수동 판독 필요']}건", border=True)
        st.dataframe(pd.DataFrame(reco_rows), hide_index=True, width="stretch",
                     column_config={"신뢰도": CONF_COL})
        with st.expander("📐 Grad-CAM 해석 가이드 (집중 영역 판정 기준)"):
            st.dataframe(XAI_GUIDE, hide_index=True, width="stretch")
        st.caption("※ XAI 결과는 자동 확정 기준이 아니라 재검토 필요 후보를 제안하는 보조 지표이며, "
                   "최종 판단·태그 수정은 영상판독관이 수행합니다.")

    # ── 내부 검증 자료 (모델 성능 · SHAP) — 판독 메인에서 강등 (수정 액션플랜 §4) ──
    with st.expander("🔧 내부 검증 자료 — 모델 성능 지표 · SHAP 기여도 (향후 고도화)"):
        h1, h2 = st.columns([4, 1], vertical_alignment="center")
        h1.markdown("##### 📐 모델 성능 요약")
        with h2.popover("❓ 지표 설명"):
            for k, txt in HELP.items():
                st.markdown(f"**{k}** — {txt}")
        cols = st.columns(len(model["지표"]))
        for col, (k, (v, kpi, _)) in zip(cols, model["지표"].items()):
            col.metric(k, f"{v:.2f}", delta=f"{(v - kpi):+.2f} (KPI {kpi:.2f})",
                       border=True, help=HELP[k] + " 높을수록 좋습니다.")

        c_kpi, c_shap = st.columns([1, 1.1], gap="medium")
        with c_kpi:
            st.markdown("##### 📊 KPI 비교 (이전 모델 대비)")
            kpi_df = pd.DataFrame([
                {"지표": k, "이번 모델": v, "이전 모델": prev, "변화": v - prev}
                for k, (v, _, prev) in model["지표"].items()])
            st.dataframe(
                kpi_df, hide_index=True, width="stretch",
                column_config={
                    "이번 모델": st.column_config.NumberColumn(format="%.2f"),
                    "이전 모델": st.column_config.NumberColumn(format="%.2f"),
                    "변화": st.column_config.NumberColumn(format="+%.2f"),
                })
            st.caption("※ 검증 데이터 기준이며, 값이 높을수록 성능이 우수함을 의미합니다.")
            with st.expander("클래스별 AP 상세"):
                ap_df = pd.DataFrame([{"클래스": k, "AP": v} for k, v in model["클래스AP"].items()])
                st.dataframe(ap_df, hide_index=True, width="stretch",
                             column_config={"AP": st.column_config.ProgressColumn(
                                 "AP", min_value=0.0, max_value=1.0, format="percent")})
        with c_shap:
            st.markdown("##### 📈 SHAP 기여도 히스토그램")
            st.altair_chart(_shap_chart(model["SHAP"]), width="stretch")
            st.caption("SHAP은 모델 취약 조건을 검토하기 위한 내부 분석 자료로, 판독관 메인 화면에 직접 노출하지 않습니다.")
        _interpretation(model)
