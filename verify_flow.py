"""app.py 전체 흐름 검증: 로그인 게이팅 → 로그인 → 메인 대시보드 진입."""
from streamlit.testing.v1 import AppTest

# 1) 비로그인 상태: 로그인 페이지만 노출
at = AppTest.from_file("app.py", default_timeout=60)
at.run()
assert not at.exception, at.exception
assert len(at.text_input) == 2, "로그인 입력 위젯이 없습니다"
print("1. 비로그인 게이팅: OK")

# 2) 로그인 폼 제출 → 메인 대시보드 진입
at.text_input[0].input("user")
at.text_input[1].input("1234")
at.button[0].click()
at.run()
assert not at.exception, at.exception
assert at.session_state["logged_in"] is True, "로그인 실패"
labels = [m.label for m in at.metric]
print("2. 로그인 후 메인 대시보드 메트릭:", labels)
assert len(at.metric) == 6, f"메트릭 6개 기대, 실제 {len(at.metric)}"

# 3) 지휘관 로그인 → 지휘관 요약 진입
at2 = AppTest.from_file("app.py", default_timeout=60)
at2.run()
at2.text_input[0].input("cmd")
at2.text_input[1].input("1234")
at2.button[0].click()
at2.run()
assert not at2.exception, at2.exception
assert at2.session_state["user"]["role"] == "지휘관", "지휘관 역할 진입 실패"
print("3. 지휘관 로그인 → 지휘관 요약 진입: OK")
print("전체 흐름 검증 통과")
