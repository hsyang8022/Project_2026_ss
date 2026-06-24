"""사용자 정보 페이지 — 공식 2역할(영상판독관·지휘관) 안내와 역할별 서비스 활용 가이드."""
from __future__ import annotations

import streamlit as st

from common import ROLE_CMD, ROLE_READER, current_user, render_header

ROLE_CARDS = [
    (ROLE_READER, "🎖️", [
        "EO/SAR 영상 조회 및 AI 탐지 결과 검토",
        "신뢰성 검토(Grad-CAM)·판독 권고 확인",
        "시간대별 변화 분석 및 표적 후보 유형 확인",
        "판독관 의견 저장 및 분석 로그·인수인계",
    ]),
    (ROLE_CMD, "⭐", [
        "재확인 필요 표적 후보 요약 확인",
        "표적 후보 유형·시간대별 변화 요약 확인",
        "후속 조치 기록(지속 감시·추가 정찰 요청·대응 준비·상급 보고)",
        "분석 로그 기반 지휘관 요약 보고서 출력",
    ]),
]

GUIDE_READER = [
    ("1. 영상 선택", "좌측 사이드바의 SAR/EO 폴더 트리에서 분석할 영상을 선택합니다."),
    ("2. 지역 탐지 확인", "SAR/EO 분석 페이지의 '지역 탐지' 탭에서 관심 구역(AOI)을 확인합니다."),
    ("3. 객체 식별 검토", "'객체 식별' 탭에서 신뢰도 임계값을 조절하며 탐지 결과와 표적 후보 유형을 검토합니다."),
    ("4. 신뢰성 확인", "신뢰성 검토 페이지에서 Grad-CAM 집중 영역과 판독 권고(신뢰/재확인/수동 판독)를 확인합니다."),
    ("5. 변화 분석", "비교·변화 분석 페이지에서 동일 구역 이전/현재 시점을 비교해 신규·소실·위치 변화를 확인합니다."),
    ("6. 의견·인수인계", "판독관 의견을 저장하고, 분석 로그·인수인계 페이지에서 교대 근무자에게 결과를 전달합니다."),
]

GUIDE_CMD = [
    ("1. 요약 확인", "지휘관 요약 페이지에서 재확인 필요 표적 후보와 표적 유형·변화 요약을 확인합니다."),
    ("2. 근거 검토", "판독관이 남긴 의견과 AI 탐지 근거를 함께 검토합니다."),
    ("3. 조치 기록", "지속 감시·추가 정찰 요청·대응 준비·상급 보고 등 후속 조치를 기록합니다."),
    ("4. 보고서 출력", "분석 로그를 기반으로 지휘관 요약 보고서를 인쇄 서식으로 내보냅니다."),
]


def user_info_page() -> None:
    render_header("사용자 정보", "공식 사용자 역할(영상판독관·지휘관)에 따라 제공되는 기능을 안내합니다.")
    u = current_user()
    st.markdown(f"**{u['rank']} {u['name']}** · {u['role']} · 군번 {u['sn']}")

    st.markdown("##### 🪪 사용자 역할 안내")
    for role, icon, features in ROLE_CARDS:
        with st.container(border=True):
            c_icon, c_body = st.columns([1, 8], vertical_alignment="center")
            c_icon.markdown(f"## {icon}")
            with c_body:
                badge = " :blue-badge[내 역할]" if role == u["role"] else ""
                st.markdown(f"**{role}**{badge}")
                st.caption(" · ".join(features))
    st.divider()

    guide = GUIDE_CMD if u["role"] == ROLE_CMD else GUIDE_READER
    st.markdown("##### 📖 서비스 활용 안내")
    for title, body in guide:
        with st.expander(title):
            st.write(body)

    st.caption("ℹ️ 모델 성능 검토·SHAP 분석·시스템 유지보수는 본 서비스의 핵심 시나리오가 아닌 "
               "내부 검증 또는 향후 고도화 기능으로 분리되어 있습니다.")
