"""청출어람 — EO/SAR 위성영상 기반 표적 후보 탐지 및 판독 지원 서비스.

실행: streamlit run app.py
"""
import streamlit as st

from common import ASSET_DIR, ROLE_CMD, current_user, ensure_data, init_state
from views.analysis import eo_page, sar_page
from views.change_analysis import change_analysis_page
from views.commander import commander_page
from views.compare import compare_page
from views.handover import handover_page
from views.home import home_page
from views.login import login_page
from views.reliability import reliability_page
from views.user_info import user_info_page

st.set_page_config(
    page_title="청출어람 — EO/SAR 표적 후보 판독 지원",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 1080p(23인치 100% 배율) 한 화면 수용을 위해 기본 상(128px)/하(160px) 패딩 축소.
# 상단은 고정 내비게이션 바(~60px)에 가리지 않는 최소값.
st.markdown(
    "<style>[data-testid='stMainBlockContainer']"
    "{padding-top:4.5rem;padding-bottom:1rem;}</style>",
    unsafe_allow_html=True,
)

ensure_data()
init_state()
st.logo(str(ASSET_DIR / "logo.png"), size="large")

if st.session_state.logged_in:
    user = current_user()
    if user and user["role"] == ROLE_CMD:
        # 지휘관: 요약·조치 기록·보고서 + 인수인계(조회) (수정 액션플랜 §1)
        pages = [
            st.Page(commander_page, title="지휘관 요약", icon="⭐", default=True),
            st.Page(handover_page, title="분석 로그·인수인계", icon="🧾"),
            st.Page(user_info_page, title="사용자 정보", icon="👤"),
        ]
    else:
        # 영상판독관: 탐지 검토 → 신뢰성·변화 분석 → 인수인계 전체 흐름
        pages = [
            st.Page(home_page, title="메인 대시보드", icon="🏠", default=True),
            st.Page(sar_page, title="SAR 분석", icon="📡"),
            st.Page(eo_page, title="EO 분석", icon="🛰️"),
            st.Page(reliability_page, title="신뢰성 검토", icon="🔬"),
            st.Page(compare_page, title="비교 분석", icon="🆚"),
            st.Page(change_analysis_page, title="시간대별 변화 분석", icon="⏱️"),
            st.Page(handover_page, title="분석 로그·인수인계", icon="🧾"),
            st.Page(user_info_page, title="사용자 정보", icon="👤"),
        ]
    pg = st.navigation(pages, position="top")
else:
    pg = st.navigation([st.Page(login_page, title="로그인", icon="🔐")], position="hidden")

pg.run()
