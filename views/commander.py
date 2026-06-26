"""지휘관 요약 · 조치 기록 · 보고서 (수정 액션플랜 §1·§3, Gate 3).

지휘관은 판독관이 검토한 표적 후보 정보를 바탕으로 지속 감시·추가 정찰 요청·대응 준비·상급 보고 등
후속 조치를 기록한다. 본 서비스는 자동 타격 권고나 화력유도 자동화 기능을 제공하지 않는다.
"""
from __future__ import annotations

import datetime as dt
import html

import pandas as pd
import streamlit as st

from common import (COMMANDER_ACTIONS, COMMANDER_COLS, COMMANDER_PATH, SENSORS,
                    TARGET_TYPE_GUIDE, append_csv_row, change_totals, classify_target_type,
                    current_user, donut_chart, list_scenes, load_commander_actions,
                    load_detections, render_header, review_needed_count, scene_meta)

ACTION_STATUS_ORDER = ["조치완료", "미조치"]
ACTION_STATUS_COLORS = ["#1f6fde", "#b8c4d6"]


def _candidates() -> pd.DataFrame:
    """전 구역 표적 후보 요약 — 표적 유형·재확인 필요 수·권장 조치."""
    det = load_detections()
    rows = []
    for sensor in SENSORS:
        for scene in list_scenes(sensor):
            sub = det[(det["센서"] == sensor) & (det["파일명"] == scene)]
            if not len(sub):
                continue
            m = scene_meta(scene)
            ttype = classify_target_type(sub)
            rows.append({
                "구역": m["구역"], "시각": m["시각"], "센서": sensor,
                "표적 후보 유형": ttype, "후보 수": len(sub),
                "재확인 필요": int((sub["신뢰도"] < 0.7).sum()),
                "권장 조치": TARGET_TYPE_GUIDE[ttype], "_scene": scene,
            })
    df = pd.DataFrame(rows)
    return df.sort_values(["재확인 필요", "후보 수"], ascending=False).reset_index(drop=True)


def _report_html(cand: pd.DataFrame, changes: dict, n_review: int, actions: pd.DataFrame) -> str:
    """분석 로그 기반 지휘관 요약 보고서 — 인쇄 서식 HTML (Gate 3)."""
    u = current_user()
    author = f"{u['rank']} {u['name']}" if u else "-"
    now = dt.datetime.now()
    cand_view = cand.drop(columns=["_scene"]) if "_scene" in cand else cand
    style = ("body{font-family:'Malgun Gothic',sans-serif;margin:32px;color:#1c2b41}"
             "h1{font-size:20px}h2{font-size:15px;border-bottom:2px solid #1f6fde;padding-bottom:4px}"
             "table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0}"
             "th,td{border:1px solid #c8d2e0;padding:5px 8px;text-align:center}"
             "th{background:#eef3fb}.kpi{display:inline-block;margin-right:24px;font-size:13px}"
             ".note{color:#6b7785;font-size:11px;margin-top:18px}")
    kpis = (f"<span class='kpi'>재확인 필요 <b>{n_review}</b>건</span>"
            f"<span class='kpi'>신규 등장 <b>{changes['신규']}</b>건</span>"
            f"<span class='kpi'>소실 <b>{changes['소실']}</b>건</span>"
            f"<span class='kpi'>위치·클래스 변화 <b>{changes['위치 변화'] + changes['클래스 변화']}</b>건</span>")
    return (f"<html><head><meta charset='utf-8'><style>{style}</style></head><body>"
            f"<h1>🛰️ 청출어람 — 지휘관 요약 보고서</h1>"
            f"<p>작성일시: {now:%Y-%m-%d %H:%M} · 작성자: {html.escape(author)}</p>"
            f"<h2>1. 분석 요약</h2><p>{kpis}</p>"
            f"<h2>2. 표적 후보 현황</h2>{cand_view.to_html(index=False)}"
            f"<h2>3. 지휘관 조치 기록</h2>"
            f"{actions.to_html(index=False) if len(actions) else '<p>기록된 조치가 없습니다.</p>'}"
            f"<p class='note'>※ 본 보고서는 영상판독관이 검토한 표적 후보를 바탕으로 한 판독 보조 자료이며, "
            f"자동 타격 권고·화력유도 자동화·현재 위치 확정 기능을 제공하지 않습니다. "
            f"모든 결과는 지휘관의 최종 판단을 보조하기 위한 참고 정보입니다.</p>"
            f"</body></html>")


def commander_page() -> None:
    render_header("지휘관 요약", "재확인 필요 표적 후보를 확인하고 후속 조치를 기록·보고합니다.")

    changes = change_totals()  # 보고서 KPI용
    n_review = review_needed_count()  # 보고서 KPI용
    cand = _candidates()
    actions = load_commander_actions()

    # ── 표적 후보 우선순위 + 조치 현황 도넛 ──
    top_l, top_r = st.columns([1.6, 1], gap="medium")
    with top_l:
        st.markdown("##### 🎯 표적 후보 우선순위 (재확인 필요 우선)")
        st.dataframe(cand.drop(columns=["_scene"]), hide_index=True, width="stretch",
                     column_config={"재확인 필요": st.column_config.NumberColumn(format="%d건")})
        st.caption("단일=정밀 확인 / 지역=구역 단위 재확인 / 광역=지속 감시 및 우선순위 검토 대상")
    with top_r:
        st.markdown("##### 🍩 조치 현황")
        if len(cand):
            acted = {p[:-4] if str(p).endswith(".png") else str(p)
                     for p in actions["대상 영상"]} if len(actions) else set()
            n_done = int(cand["_scene"].isin(acted).sum())
            counts = pd.DataFrame({"상태": ACTION_STATUS_ORDER,
                                   "건수": [n_done, len(cand) - n_done]})
            st.altair_chart(
                donut_chart(counts, len(cand), ACTION_STATUS_ORDER, ACTION_STATUS_COLORS),
                width="stretch")
            st.caption(f"전체 표적 후보 {len(cand)}건 중 조치완료 {n_done}건")
        else:
            st.info("표적 후보가 없습니다.")

    # ── 후속 조치 기록 폼 + 최근 조치 (타격성 표현 배제) ──
    form_l, form_r = st.columns([1.4, 1], gap="medium")
    with form_l:
        if st.toggle("⭐ 후속 조치 기록 작성", key="cmd_action_toggle"):
            with st.form("commander_action", clear_on_submit=True):
                labels = [f"{r['구역']} {r['시각']} · {r['센서']} ({r['표적 후보 유형']})"
                          for _, r in cand.iterrows()]
                idx = st.selectbox("대상 표적 후보", range(len(labels)),
                                   format_func=lambda i: labels[i]) if labels else None
                action = st.selectbox("조치 유형", COMMANDER_ACTIONS)
                content = st.text_area("조치 내용", height=80, max_chars=500,
                                       placeholder="예: 야간 추가 정찰 요청, 상급 부대 보고")
                basis = st.text_input("근거 요약", placeholder="예: 신규 차량 2대 + 재확인 필요 3건")
                saved = st.form_submit_button("조치 기록 저장", type="primary", width="stretch")
            if saved and idx is not None:
                r = cand.iloc[idx]
                u = current_user()
                append_csv_row(COMMANDER_PATH, {
                    "작성시간": f"{dt.datetime.now():%Y-%m-%d %H:%M}",
                    "작성자": f"{u['rank']} {u['name']}" if u else "-",
                    "대상 영상": f"{r['_scene']}.png", "센서": r["센서"],
                    "위치": f"{r['구역']} {r['시각']}", "표적유형": r["표적 후보 유형"],
                    "조치유형": action, "조치 내용": content, "근거 요약": basis,
                }, COMMANDER_COLS)
                st.toast("지휘관 조치가 기록되었습니다.", icon="✅")
                st.rerun()
            st.caption("ℹ️ 본 서비스는 자동 타격 권고·화력유도 자동화 기능을 제공하지 않습니다.")
    with form_r:
        st.markdown("##### 🗂️ 최근 지휘관 조치 기록")
        st.dataframe(actions.iloc[::-1].head(5), hide_index=True, width="stretch")

    st.download_button(
        "🖨️ 지휘관 요약 보고서 출력 (인쇄 서식 HTML)",
        _report_html(cand, changes, n_review, actions).encode("utf-8"),
        file_name=f"commander_report_{dt.datetime.now():%Y%m%d_%H%M}.html",
        mime="text/html", type="primary",
    )
    st.caption("브라우저에서 열어 인쇄(Ctrl+P) 시 PDF로 저장할 수 있습니다.")
