"""로그인 페이지 — 아이디/비밀번호 입력, 권한별 세션 부여, 로그인 기록 저장."""
from __future__ import annotations

import datetime as dt

import streamlit as st

from common import ACCOUNTS, LOGIN_COLS, LOGIN_HISTORY_PATH, append_csv_row


def login_page() -> None:
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown("## 🛰️ 청출어람")
        st.markdown("**EO/SAR 위성영상 기반 표적 후보 탐지 및 판독 지원 서비스**")
        st.caption("계정으로 로그인하면 역할(영상판독관·지휘관)에 따라 사용 가능한 기능이 구분됩니다.")

        with st.form("login_form"):
            uid = st.text_input("아이디")
            pw = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", type="primary", width="stretch")

        if submitted:
            acct = ACCOUNTS.get(uid)
            success = acct is not None and acct["pw"] == pw
            append_csv_row(LOGIN_HISTORY_PATH, {
                "일시": f"{dt.datetime.now():%Y-%m-%d %H:%M}",
                "아이디": uid or "-",
                "성명": acct["name"] if success else "-",
                "역할": acct["role"] if success else "-",
                "결과": "성공" if success else "실패(인증 오류)",
            }, LOGIN_COLS)
            if success:
                st.session_state.logged_in = True
                st.session_state.user = {"id": uid, **acct}
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        with st.expander("데모 계정 안내"):
            st.caption("`user` / 1234 — 영상판독관 (탐지 검토·신뢰성·변화 분석·인수인계)")
            st.caption("`cmd` / 1234 — 지휘관 (요약·조치 기록·보고서)")
