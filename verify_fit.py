"""지정 페이지가 1080p(23인치 100% 배율) 뷰포트에 스크롤 없이 들어가는지 측정.

사전 조건: streamlit run app.py --server.port 8504 실행 중.
사용: python verify_fit.py [페이지명]   (기본: 비교 분석)
"""
import sys

from playwright.sync_api import sync_playwright

URL = "http://localhost:8504"
# 1920×1080에서 Windows 작업표시줄 + 브라우저 UI를 제외한 일반적인 뷰포트 높이
VIEWPORT = {"width": 1920, "height": 940}
PAGE_NAME = sys.argv[1] if len(sys.argv) > 1 else "비교 분석"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport=VIEWPORT)
    page.goto(URL, wait_until="networkidle")

    # 로그인
    page.get_by_label("아이디").fill("user")
    page.get_by_label("비밀번호").fill("1234")
    page.get_by_role("button", name="로그인").click()
    page.wait_for_timeout(2500)

    # 상단 내비게이션에서 대상 페이지로 이동
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_timeout(3000)

    metrics = page.evaluate(
        """() => {
            const main = document.querySelector('[data-testid="stMain"]')
                || document.querySelector('section.main') || document.body;
            return {scrollHeight: main.scrollHeight, clientHeight: main.clientHeight};
        }"""
    )
    page.screenshot(path=f"{PAGE_NAME.replace(' ', '_')}_fit.png")
    browser.close()

overflow = metrics["scrollHeight"] - metrics["clientHeight"]
print(f"scrollHeight={metrics['scrollHeight']}, clientHeight={metrics['clientHeight']}, overflow={overflow}px")
print("FIT OK" if overflow <= 0 else f"OVERFLOW {overflow}px - 추가 압축 필요")
