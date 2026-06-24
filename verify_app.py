"""페이지별 렌더링 검증 스크립트: python verify_app.py

Streamlit AppTest로 각 페이지 함수를 실행하여 예외 발생 여부를 확인한다.
"""
from __future__ import annotations

import sys

from streamlit.testing.v1 import AppTest

from common import ACCOUNTS


def _page_script(name: str) -> None:
    import importlib

    mod_name, fn_name = name.split(":")
    fn = getattr(importlib.import_module(mod_name), fn_name)
    fn()


PAGES = [
    "views.login:login_page",
    "views.home:home_page",
    "views.analysis:sar_page",
    "views.analysis:eo_page",
    "views.reliability:reliability_page",
    "views.compare:compare_page",
    "views.change_analysis:change_analysis_page",
    "views.handover:handover_page",
    "views.commander:commander_page",
]


def run_one(name: str, role_id: str = "user") -> bool:
    at = AppTest.from_function(_page_script, args=(name,), default_timeout=60)
    at.session_state["logged_in"] = True
    at.session_state["user"] = {"id": role_id, **ACCOUNTS[role_id]}
    at.run()
    label = f"{name} (role={role_id})"
    if at.exception:
        print(f"[FAIL] {label}")
        for e in at.exception:
            print("       ", e.value)
        return False
    print(f"[OK]   {label}")
    return True


def main() -> int:
    ok = all([run_one(p) for p in PAGES])
    for role in ACCOUNTS:
        ok = run_one("views.user_info:user_info_page", role) and ok
    print("결과:", "전체 통과" if ok else "실패 있음")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
