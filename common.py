"""공통 모듈: 경로 상수, 계정, 세션 상태, 공통 헤더/사이드바, 데이터 로더."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = DATA_DIR / "images"
XAI_DIR = DATA_DIR / "xai"
ASSET_DIR = DATA_DIR / "assets"
UPLOAD_DIR = DATA_DIR / "uploads"

SENSORS = ("SAR", "EO")
FOLDERS = ("원본", "지역탐지", "객체식별")

CLASSES = {
    "SAR": ["전차", "장갑차", "자주포", "군용트럭"],
    "EO": ["전투기", "수송기", "헬기", "지상차량"],
}
PALETTE = {
    "전차": (230, 57, 70), "장갑차": (255, 140, 0), "자주포": (155, 89, 182), "군용트럭": (52, 152, 219),
    "전투기": (230, 57, 70), "수송기": (255, 140, 0), "헬기": (155, 89, 182), "지상차량": (52, 152, 219),
}

# 공식 사용자: 영상판독관 + 지휘관 (수정 액션플랜 §1). 데이터사이언티스트·유지보수는 공식 UI에서 제외.
ROLE_READER = "영상판독관"
ROLE_CMD = "지휘관"

ACCOUNTS = {
    "user": {"pw": "1234", "rank": "대위", "name": "김OO", "role": ROLE_READER, "sn": "23-00001"},
    "cmd": {"pw": "1234", "rank": "중령", "name": "최OO", "role": ROLE_CMD, "sn": "12-00045"},
}

OPINION_PATH = DATA_DIR / "opinions.csv"
OPINION_COLS = ["작성시간", "파일명", "센서", "수집일", "위치", "평가", "결과 요약", "상세 의견", "탐지수", "신뢰도 범위"]
LOGIN_HISTORY_PATH = DATA_DIR / "login_history.csv"
LOGIN_COLS = ["일시", "아이디", "성명", "역할", "결과"]

# 지휘관 조치 기록 (수정 액션플랜 §3 — 타격성 표현 배제). 분석 로그와 분리 저장.
COMMANDER_PATH = DATA_DIR / "commander_actions.csv"
COMMANDER_COLS = ["작성시간", "작성자", "대상 영상", "센서", "위치", "표적유형",
                  "조치유형", "조치 내용", "근거 요약"]
COMMANDER_ACTIONS = ["지속 감시", "추가 정찰 요청", "대응 준비", "상급 보고 / 결심 사항 기록"]

# 시간대별 변화 분석 메모
CHANGE_MEMO_PATH = DATA_DIR / "change_memos.csv"
CHANGE_MEMO_COLS = ["작성시간", "작성자", "센서", "구역", "이전시점", "현재시점",
                    "신규", "소실", "위치변화", "메모"]

# 표적 후보 유형 분류 기준 (기획서 §4.8)
IMG_W, IMG_H = 800, 600
TARGET_TYPE_GUIDE = {
    "단일표적 후보": "정밀 확인 대상",
    "지역표적 후보": "구역 단위 재확인 대상",
    "광역표적 후보": "지속 감시 및 우선순위 검토 대상",
}


def donut_chart(counts: pd.DataFrame, total: int, domain: list[str], colors: list[str],
                label_col: str = "상태", value_col: str = "건수",
                center_label: str | None = None, height: int = 220) -> alt.LayerChart:
    """공용 도넛 차트 — 분류별 건수 arc + 중앙 합계 텍스트 (메인 대시보드·지휘관 요약 공용).

    counts: [label_col, value_col] 컬럼을 가진 DataFrame.
    """
    base = alt.Chart(counts).encode(
        theta=alt.Theta(f"{value_col}:Q"),
        color=alt.Color(
            f"{label_col}:N",
            scale=alt.Scale(domain=domain, range=colors),
            legend=alt.Legend(title=None, orient="right", labelFontSize=13),
        ),
        tooltip=[f"{label_col}:N", f"{value_col}:Q"],
    )
    donut = base.mark_arc(innerRadius=58, outerRadius=86)
    center = alt.Chart(pd.DataFrame({"라벨": [center_label or f"{total}건"]})).mark_text(
        size=28, fontWeight="bold", color="#1c2b41"
    ).encode(text="라벨:N")
    return (donut + center).properties(height=height)


def get_font(size: int):
    for name in ("malgunbd.ttf", "malgun.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def ensure_data() -> None:
    if not (IMG_DIR / "SAR" / "원본").exists() or not (DATA_DIR / "regions.csv").exists():
        import generate_dummy_data
        generate_dummy_data.main()


def init_state() -> None:
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("user", None)


def current_user() -> dict | None:
    return st.session_state.get("user")


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.user = None


def render_header(title: str, caption: str | None = None, compact: bool = False) -> None:
    """페이지 상단 공통 헤더 — 좌측 제목, 우측 회원 정보(기획서: 우측 상단 회원 정보 표시).

    compact=True: 한 화면(1080p, 100% 배율)에 모든 기능을 담아야 하는 페이지용 —
    제목 크기 축소, 캡션·구분선 생략으로 수직 공간을 절약한다.
    """
    left, right = st.columns([5, 1.3], vertical_alignment="center")
    with left:
        if compact:
            st.markdown(f"#### {title}")
        else:
            st.subheader(title)
            if caption:
                st.caption(caption)
    with right:
        user_badge()
    if not compact:
        st.divider()


def user_badge() -> None:
    """우측 상단 회원 정보 popover + 로그아웃 버튼."""
    u = current_user()
    if u:
        with st.popover(f"👤 {u['rank']} {u['name']}", width="stretch"):
            st.markdown(f"**{u['rank']} {u['name']}**")
            st.caption(f"{u['role']} · 군번 {u['sn']}")
            if st.button("로그아웃", key="logout_btn", width="stretch"):
                logout()
                st.rerun()


def list_scenes(sensor: str) -> list[str]:
    return sorted(p.stem for p in (IMG_DIR / sensor / "원본").glob("*.png"))


def img_path(sensor: str, folder: str, scene: str) -> Path:
    return IMG_DIR / sensor / folder / f"{scene}.png"


def xai_path(sensor: str, scene: str, with_boxes: bool = False) -> Path:
    suffix = "_boxes" if with_boxes else ""
    return XAI_DIR / sensor / f"{scene}{suffix}.png"


def scene_meta(scene: str) -> dict:
    sensor, ymd, zone, idx = scene.split("_")
    date = dt.datetime.strptime(ymd, "%Y%m%d").date()
    # idx는 촬영 시각(HHMM) — 시간대별 변화 분석을 위한 시점 구분에 사용
    time = f"{idx[:2]}:{idx[2:]}" if len(idx) == 4 and idx.isdigit() else idx
    return {"센서": sensor, "수집일": f"{date:%Y-%m-%d}", "구역": zone, "시각": time, "번호": idx}


def scene_pairs(sensor: str) -> dict[str, list[str]]:
    """동일 (수집일·구역)의 시점별 영상을 묶어 반환 — 시간대별 변화 분석용.

    반환: {"YYYY-MM-DD · A구역": ["SAR_..._1000", "SAR_..._1030"], ...} (시각 오름차순)
    """
    groups: dict[str, list[str]] = {}
    for s in list_scenes(sensor):
        m = scene_meta(s)
        groups.setdefault(f"{m['수집일']} · {m['구역']}", []).append(s)
    for key in groups:
        groups[key] = sorted(groups[key], key=lambda s: scene_meta(s)["번호"])
    return groups


def classify_target_type(det_rows: pd.DataFrame) -> str:
    """탐지 객체 수·공간 분포 기반 rule-based 표적 후보 유형 분류 (기획서 §4.8).

    단일: 객체 1개 / 지역: 일정 구역 밀집 / 광역: 객체가 많고 넓게 분포.
    """
    n = len(det_rows)
    if n <= 1:
        return "단일표적 후보"
    cx = det_rows["x"] + det_rows["w"] / 2
    cy = det_rows["y"] + det_rows["h"] / 2
    spread = float(((cx.max() - cx.min()) ** 2 + (cy.max() - cy.min()) ** 2) ** 0.5)
    diag = (IMG_W ** 2 + IMG_H ** 2) ** 0.5
    if n >= 5 and spread / diag >= 0.45:
        return "광역표적 후보"
    return "지역표적 후보"


def match_detections(prev: pd.DataFrame, curr: pd.DataFrame,
                     dist_thresh: float = 70.0, move_thresh: float = 25.0) -> pd.DataFrame:
    """이전/현재 탐지 결과를 bbox 중심좌표 거리로 매칭해 변화 상태를 부여 (기획서 §4.7).

    상태: 유지 / 신규 / 소실 / 위치 변화 / 클래스 변화 / 불확실.
    """
    def center(r):
        return (r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)

    prev_rows = prev.to_dict("records")
    curr_rows = curr.to_dict("records")
    used_prev: set[int] = set()
    out: list[dict] = []

    for c in curr_rows:
        ccx, ccy = center(c)
        best_i, best_d = -1, dist_thresh
        for i, p in enumerate(prev_rows):
            if i in used_prev:
                continue
            pcx, pcy = center(p)
            d = ((ccx - pcx) ** 2 + (ccy - pcy) ** 2) ** 0.5
            if d <= best_d:
                best_i, best_d = i, d
        if best_i >= 0:
            used_prev.add(best_i)
            p = prev_rows[best_i]
            low_conf = min(p["신뢰도"], c["신뢰도"]) < 0.6
            if p["클래스"] != c["클래스"]:
                state = "클래스 변화"
            elif low_conf:
                state = "불확실"
            elif best_d > move_thresh:
                state = "위치 변화"
            else:
                state = "유지"
            out.append({"상태": state, "이전 객체": p["객체ID"], "현재 객체": c["객체ID"],
                        "클래스": f"{p['클래스']}→{c['클래스']}" if p["클래스"] != c["클래스"] else c["클래스"],
                        "이동(px)": round(best_d, 1), "신뢰도": round(c["신뢰도"], 2)})
        else:
            out.append({"상태": "신규", "이전 객체": "—", "현재 객체": c["객체ID"],
                        "클래스": c["클래스"], "이동(px)": None, "신뢰도": round(c["신뢰도"], 2)})

    for i, p in enumerate(prev_rows):
        if i not in used_prev:
            out.append({"상태": "소실", "이전 객체": p["객체ID"], "현재 객체": "—",
                        "클래스": p["클래스"], "이동(px)": None, "신뢰도": round(p["신뢰도"], 2)})

    order = {"신규": 0, "소실": 1, "위치 변화": 2, "클래스 변화": 3, "불확실": 4, "유지": 5}
    return pd.DataFrame(out).sort_values("상태", key=lambda s: s.map(order)).reset_index(drop=True)


def scene_status() -> dict[str, str]:
    """분석 로그 기준 파일별 상태: 모든 로그가 완료면 '분석완료', 아니면 '미분석'."""
    log = load_analysis_log()
    grouped = log.groupby("파일명")["상태"].apply(lambda s: "분석완료" if (s == "완료").all() else "미분석")
    return grouped.to_dict()


def render_sidebar_tree() -> None:
    """좌측 사이드바 폴더 탐색 트리 — 수집데이터(날짜별)/미분석자료/분석완료 가상 구조."""
    status = scene_status()
    with st.sidebar:
        st.markdown("#### 📂 폴더 탐색")
        for sensor in SENSORS:
            with st.expander(f"🛰️ {sensor}"):
                scenes = list_scenes(sensor)
                by_date: dict[str, list[str]] = {}
                for s in scenes:
                    by_date.setdefault(scene_meta(s)["수집일"], []).append(s)
                st.markdown("**00_수집데이터/**")
                for date in sorted(by_date, reverse=True):
                    st.caption(f"📁 {date} ({len(by_date[date])}건)")
                pending = [s for s in scenes if status.get(f"{s}.png") != "분석완료"]
                done = [s for s in scenes if status.get(f"{s}.png") == "분석완료"]
                st.markdown("**01_미분석자료/**")
                for s in pending:
                    st.caption(f"└ {s}.png")
                st.markdown("**02_분석완료/**")
                for s in done:
                    st.caption(f"└ {s}.png")


def sidebar_scene_picker(sensor: str) -> str:
    """분석 페이지용 사이드바 — 영상 선택 + 처리 단계별(수집/지역탐지/객체식별) 썸네일 미리보기."""
    folder_labels = {"원본": "수집 원본 이미지", "지역탐지": "지역 탐지 이미지", "객체식별": "객체 식별 이미지"}
    with st.sidebar:
        st.markdown(f"#### 🗂️ {sensor} 데이터 및 이미지 선택")
        scenes = list_scenes(sensor)
        scene = st.radio("분석 대상 영상", scenes, key=f"scene_{sensor}")
        st.divider()
        for i, folder in enumerate(FOLDERS, 1):
            st.markdown(f"**{i}. {folder_labels[folder]}**")
            st.image(str(img_path(sensor, folder, scene)), width="stretch")
    return scene


@st.cache_data(show_spinner=False)
def load_detections() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "detections.csv", encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def load_regions() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "regions.csv", encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def load_analysis_log() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "analysis_log.csv", encoding="utf-8-sig")
    df["일시"] = pd.to_datetime(df["일시"])
    return df


@st.cache_data(show_spinner=False)
def load_system_log() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "system_log.csv", encoding="utf-8-sig")


def append_csv_row(path: Path, row: dict, columns: list[str]) -> None:
    new = pd.DataFrame([row], columns=columns)
    if path.exists():
        new = pd.concat([pd.read_csv(path, encoding="utf-8-sig"), new], ignore_index=True)
    new.to_csv(path, index=False, encoding="utf-8-sig")


def load_opinions() -> pd.DataFrame:
    if OPINION_PATH.exists():
        return pd.read_csv(OPINION_PATH, encoding="utf-8-sig")
    return pd.DataFrame(columns=OPINION_COLS)


def load_login_history() -> pd.DataFrame:
    if LOGIN_HISTORY_PATH.exists():
        return pd.read_csv(LOGIN_HISTORY_PATH, encoding="utf-8-sig")
    return pd.DataFrame(columns=LOGIN_COLS)


def load_commander_actions() -> pd.DataFrame:
    if COMMANDER_PATH.exists():
        return pd.read_csv(COMMANDER_PATH, encoding="utf-8-sig")
    return pd.DataFrame(columns=COMMANDER_COLS)


def load_change_memos() -> pd.DataFrame:
    if CHANGE_MEMO_PATH.exists():
        return pd.read_csv(CHANGE_MEMO_PATH, encoding="utf-8-sig")
    return pd.DataFrame(columns=CHANGE_MEMO_COLS)


def change_totals() -> dict[str, int]:
    """전 센서·전 구역 시간대별 변화 상태 집계 — 메인 대시보드·지휘관 요약 공용 (기획서 §4.2·4.7)."""
    det = load_detections()
    tot = {"신규": 0, "소실": 0, "위치 변화": 0, "클래스 변화": 0, "불확실": 0, "유지": 0}
    for sensor in SENSORS:
        for scenes in scene_pairs(sensor).values():
            if len(scenes) < 2:
                continue
            prev = det[(det["센서"] == sensor) & (det["파일명"] == scenes[0])]
            curr = det[(det["센서"] == sensor) & (det["파일명"] == scenes[-1])]
            for state, n in match_detections(prev, curr)["상태"].value_counts().items():
                tot[state] = tot.get(state, 0) + int(n)
    return tot


def review_needed_count(threshold: float = 0.7) -> int:
    """재확인 필요 객체 후보 수 — 신뢰도 임계값 미만(수동 판독/재확인 대상)."""
    det = load_detections()
    return int((det["신뢰도"] < threshold).sum())


@st.cache_data(show_spinner=False)
def detection_overlay(sensor: str, scene: str, threshold: float) -> Image.Image:
    """원본 영상 위에 임계값 이상 탐지 박스를 실시간으로 그려 반환."""
    img = Image.open(img_path(sensor, "원본", scene)).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    det = load_detections()
    rows = det[(det["센서"] == sensor) & (det["파일명"] == scene) & (det["신뢰도"] >= threshold)]
    for _, r in rows.iterrows():
        color = PALETTE.get(r["클래스"], (255, 0, 0))
        x, y, w, h = int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"])
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        label = f'{r["클래스"]} {r["신뢰도"]:.2f}'
        ly = max(2, y - 22)
        tb = draw.textbbox((x, ly), label, font=font)
        draw.rectangle([tb[0] - 3, tb[1] - 2, tb[2] + 3, tb[3] + 2], fill=color)
        draw.text((x, ly), label, font=font, fill="white")
    return img
