"""README용 페이지 스크린샷 일괄 캡처 → docs/images/

사전 조건: streamlit run app.py --server.port 8504 실행 중 + playwright(chromium) 설치.
사용: python capture_screens.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8504"
VIEWPORT = {"width": 1920, "height": 940}
OUT_DIR = Path(__file__).resolve().parent / "docs" / "images"

# (파일명, 상단 내비게이션 링크명, full_page 캡처 여부, 캡처 전 추가 동작)
PAGES = [
    ("home.png", "메인 대시보드", True, None),
    ("sar_analysis.png", "SAR 분석", True, "object_tab"),
    ("reliability.png", "신뢰성 검토", True, None),
    ("compare.png", "비교 분석", False, None),
    ("user_info.png", "사용자 정보", True, None),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(1500)

        # 1) 로그인 화면
        page.screenshot(path=OUT_DIR / "login.png")
        print("captured: login.png")

        # 로그인
        page.get_by_label("아이디").fill("user")
        page.get_by_label("비밀번호").fill("1234")
        page.get_by_role("button", name="로그인").click()
        page.wait_for_timeout(2500)

        # 2~6) 각 페이지
        for filename, nav_name, full_page, extra in PAGES:
            page.get_by_role("link", name=nav_name).click()
            page.wait_for_timeout(3000)
            if extra == "object_tab":
                page.get_by_role("tab", name="객체 식별").click()
                page.wait_for_timeout(2000)
            page.screenshot(path=OUT_DIR / filename, full_page=full_page)
            print(f"captured: {filename}")

        browser.close()
    print(f"완료 — 저장 위치: {OUT_DIR}")


if __name__ == "__main__":
    main()
