"""더미 데이터 생성: data/ 폴더에 SAR/EO 영상, 탐지 결과 CSV, 분석 로그, Grad-CAM, 로고를 생성한다.

단독 실행 가능: python generate_dummy_data.py
"""
from __future__ import annotations

import datetime as dt
import random

import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from common import (ASSET_DIR, CLASSES, DATA_DIR, FOLDERS, IMG_DIR, PALETTE,
                    SENSORS, UPLOAD_DIR, XAI_DIR, get_font)

W, H = 800, 600
ZONES = ["A구역", "B구역", "C구역", "D구역"]
ZONE_COORD = {"A구역": (37.45, 126.70), "B구역": (37.92, 126.41), "C구역": (38.21, 127.35), "D구역": (38.05, 128.02)}
TIMES = ["1000", "1030"]  # 동일 구역의 이전/현재 시점 (30분 간격) — 시간대별 변화 분석용


def zone_days() -> list[tuple[str, dt.date]]:
    today = dt.date.today()
    return [(zone, today - dt.timedelta(days=[0, 0, 1, 2][i])) for i, zone in enumerate(ZONES)]


def scene_names(sensor: str) -> list[str]:
    """구역마다 2시점(10:00/10:30) 영상명을 생성: {센서}_{날짜}_{구역}_{HHMM}."""
    return [f"{sensor}_{day:%Y%m%d}_{zone}_{t}" for zone, day in zone_days() for t in TIMES]


def _coord(zone: str, x: float, y: float) -> tuple[float, float]:
    lat0, lon0 = ZONE_COORD[zone]
    return round(lat0 + (H / 2 - y) * 0.00002, 5), round(lon0 + (x - W / 2) * 0.00002, 5)


def make_detections(sensor: str, scene: str) -> list[dict]:
    """기준(이전) 시점 탐지 결과."""
    rng = random.Random(scene)
    zone = scene.split("_")[2]
    rows = []
    for i in range(rng.randint(3, 6)):
        w, h = rng.randint(26, 56), rng.randint(22, 44)
        x, y = rng.randint(60, W - 60 - w), rng.randint(60, H - 60 - h)
        lat, lon = _coord(zone, x, y)
        rows.append({
            "파일명": scene, "센서": sensor, "객체ID": f"OBJ-{i + 1:03d}",
            "클래스": rng.choice(CLASSES[sensor]),
            "신뢰도": round(rng.uniform(0.55, 0.98), 2),
            "x": x, "y": y, "w": w, "h": h, "위도": lat, "경도": lon,
        })
    return rows


def derive_next(sensor: str, curr_scene: str, prev_dets: list[dict]) -> list[dict]:
    """이전 시점 탐지로부터 현재 시점 탐지를 파생 — 신규/소실/위치 변화/클래스 변화 발생."""
    rng = random.Random(curr_scene + "next")
    zone = curr_scene.split("_")[2]
    kept = prev_dets[:-1] if len(prev_dets) > 2 else list(prev_dets)  # 마지막 1개 소실
    rows = []
    for j, p in enumerate(kept):
        w, h, cls = p["w"], p["h"], p["클래스"]
        if j == 0:  # 위치 변화: 큰 이동
            dx, dy = rng.choice([-1, 1]) * rng.randint(35, 60), rng.choice([-1, 1]) * rng.randint(35, 60)
        else:       # 소폭 이동(유지)
            dx, dy = rng.randint(-8, 8), rng.randint(-8, 8)
        x = min(W - 60 - w, max(60, p["x"] + dx))
        y = min(H - 60 - h, max(60, p["y"] + dy))
        if j == 1 and len(kept) >= 3:  # 클래스 변화 1건
            cls = rng.choice([c for c in CLASSES[sensor] if c != p["클래스"]])
        lat, lon = _coord(zone, x, y)
        rows.append({"파일명": curr_scene, "센서": sensor, "객체ID": "",
                     "클래스": cls, "신뢰도": round(rng.uniform(0.55, 0.98), 2),
                     "x": x, "y": y, "w": w, "h": h, "위도": lat, "경도": lon})
    # 신규 1건
    w, h = rng.randint(26, 56), rng.randint(22, 44)
    x, y = rng.randint(60, W - 60 - w), rng.randint(60, H - 60 - h)
    lat, lon = _coord(zone, x, y)
    rows.append({"파일명": curr_scene, "센서": sensor, "객체ID": "",
                 "클래스": rng.choice(CLASSES[sensor]), "신뢰도": round(rng.uniform(0.55, 0.98), 2),
                 "x": x, "y": y, "w": w, "h": h, "위도": lat, "경도": lon})
    for k, r in enumerate(rows):
        r["객체ID"] = f"OBJ-{k + 1:03d}"
    return rows


def sar_base(scene: str, dets: list[dict]) -> Image.Image:
    """SAR 원본: 어두운 스페클 노이즈 + 저반사 도로 + 고반사 표적 블롭."""
    rng = random.Random(scene + "img")
    img = Image.effect_noise((W, H), 30).point(lambda p: int(p * 0.5)).convert("RGB")
    d = ImageDraw.Draw(img)
    y0 = rng.randint(150, 450)
    d.line([(0, y0), (W, y0 + rng.randint(-80, 80))], fill=(20, 20, 24), width=rng.randint(14, 22))
    for r in dets:
        cx, cy = r["x"] + r["w"] // 2, r["y"] + r["h"] // 2
        d.ellipse([cx - r["w"] // 2, cy - r["h"] // 2, cx + r["w"] // 2, cy + r["h"] // 2], fill=(235, 235, 240))
        d.ellipse([cx - r["w"] // 4, cy - r["h"] // 4, cx + r["w"] // 4, cy + r["h"] // 4], fill=(255, 255, 255))
    return img.filter(ImageFilter.GaussianBlur(0.9))


def eo_base(scene: str, dets: list[dict]) -> Image.Image:
    """EO 원본: 지형 패치 + 도로 + 표적 형상."""
    rng = random.Random(scene + "img")
    img = Image.new("RGB", (W, H), (74, 96, 58))
    d = ImageDraw.Draw(img)
    for _ in range(40):
        x, y = rng.randint(-100, W), rng.randint(-100, H)
        w, h = rng.randint(60, 240), rng.randint(40, 160)
        d.rectangle([x, y, x + w, y + h],
                    fill=rng.choice([(88, 108, 62), (108, 96, 66), (64, 84, 54), (120, 112, 80)]))
    img = img.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(img)
    y0 = rng.randint(120, 480)
    d.line([(0, y0), (W, y0 + rng.randint(-60, 60))], fill=(150, 148, 140), width=rng.randint(16, 26))
    for r in dets:
        d.rectangle([r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]], fill=(70, 72, 76), outline=(40, 40, 44))
        d.rectangle([r["x"] + 4, r["y"] + 4, r["x"] + r["w"] // 2, r["y"] + r["h"] // 2], fill=(96, 98, 102))
    noise = Image.effect_noise((W, H), 18).convert("RGB")
    return Image.blend(img, noise, 0.06)


def region_bbox(dets: list[dict]) -> tuple[int, int, int, int]:
    """표적 군집을 감싸는 관심 구역(AOI) bbox."""
    x1 = max(4, min(r["x"] for r in dets) - 30)
    y1 = max(4, min(r["y"] for r in dets) - 30)
    x2 = min(W - 4, max(r["x"] + r["w"] for r in dets) + 30)
    y2 = min(H - 4, max(r["y"] + r["h"] for r in dets) + 30)
    return x1, y1, x2, y2


def region_image(base: Image.Image, dets: list[dict], font) -> Image.Image:
    """지역탐지 결과: 표적 군집을 감싸는 관심 구역 박스."""
    x1, y1, x2, y2 = region_bbox(dets)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([x1, y1, x2, y2], fill=(255, 140, 0, 36), outline=(255, 140, 0, 255), width=5)
    d.text((x1 + 8, max(4, y1 - 26) if y1 > 32 else y1 + 6), "관심 구역 R-1", font=font, fill=(255, 200, 60, 255))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def draw_boxes(img: Image.Image, dets: list[dict], font) -> Image.Image:
    """클래스별 색상 바운딩 박스 + 라벨을 img 위에 그려 반환(제자리 수정)."""
    d = ImageDraw.Draw(img)
    for r in dets:
        color = PALETTE[r["클래스"]]
        d.rectangle([r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]], outline=color, width=3)
        label = f'{r["클래스"]} {r["신뢰도"]:.2f}'
        ly = max(2, r["y"] - 22)
        tb = d.textbbox((r["x"], ly), label, font=font)
        d.rectangle([tb[0] - 3, tb[1] - 2, tb[2] + 3, tb[3] + 2], fill=color)
        d.text((r["x"], ly), label, font=font, fill="white")
    return img


def object_image(base: Image.Image, dets: list[dict], font) -> Image.Image:
    """객체식별 결과: 클래스별 색상 바운딩 박스 + 라벨."""
    return draw_boxes(base.copy(), dets, font)


def gradcam_image(base: Image.Image, dets: list[dict]) -> Image.Image:
    """Grad-CAM 히트맵: 표적 위치 중심의 집중도 오버레이."""
    heat = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(heat)
    for r in dets:
        cx, cy = r["x"] + r["w"] // 2, r["y"] + r["h"] // 2
        rad = max(r["w"], r["h"])
        d.ellipse([cx - rad * 1.6, cy - rad * 1.6, cx + rad * 1.6, cy + rad * 1.6], fill=110)
        d.ellipse([cx - rad * 0.9, cy - rad * 0.9, cx + rad * 0.9, cy + rad * 0.9], fill=210)
        d.ellipse([cx - rad * 0.45, cy - rad * 0.45, cx + rad * 0.45, cy + rad * 0.45], fill=255)
    heat = heat.filter(ImageFilter.GaussianBlur(22))
    colored = ImageOps.colorize(heat, black=(8, 12, 60), white=(255, 40, 20), mid=(255, 210, 40))
    return Image.blend(base.convert("RGB"), colored, 0.45)


def make_logo() -> None:
    img = Image.new("RGBA", (420, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, 419, 119], radius=18, fill=(15, 34, 66, 255))
    d.text((24, 14), "청출어람", font=get_font(48), fill=(255, 255, 255, 255))
    d.text((26, 80), "EO·SAR 위성영상 표적 분석", font=get_font(20), fill=(160, 190, 255, 255))
    img.save(ASSET_DIR / "logo.png")


READERS = [("대위", "김OO"), ("중위", "이OO"), ("소령", "박OO"), ("준위", "정OO"), ("상사", "강OO")]
SUMMARIES = [
    "신규 차량 2대 확인", "감시 장비 배치 관측", "지하 갱도 입구 탐지", "트럭 3대 이동 확인",
    "야간 차량 집결 징후", "관심 구역 변화 없음", "고정 진지 보강 정황", "경계 태세 구축 관측",
]


def make_logs(all_scenes: dict[str, list[str]], det_df: pd.DataFrame) -> None:
    rows = []
    for sensor, scenes in all_scenes.items():
        for scene in scenes:
            rng = random.Random(scene + "log")
            date = dt.datetime.strptime(scene.split("_")[1], "%Y%m%d")
            base_t = date.replace(hour=rng.randint(6, 9), minute=rng.randint(0, 59))
            sub = det_df[det_df["파일명"] == scene]
            for kind, offset in (("지역탐지", 0), ("객체식별", 35)):
                t = base_t + dt.timedelta(minutes=offset)
                status = rng.choice(["완료", "완료", "완료", "진행중", "대기"])
                rank, name = rng.choice(READERS)
                rows.append({
                    "일시": f"{t:%Y-%m-%d %H:%M}", "센서": sensor, "파일명": f"{scene}.png",
                    "분석유형": kind, "탐지수": len(sub),
                    "평균신뢰도": round(float(sub["신뢰도"].mean()), 2),
                    "상태": status,
                    "계급": rank if status == "완료" else "—",
                    "이름": name if status == "완료" else "—",
                    "내용": rng.choice(SUMMARIES) if status == "완료" else "판독 대기",
                })
    pd.DataFrame(rows).sort_values("일시", ascending=False).to_csv(
        DATA_DIR / "analysis_log.csv", index=False, encoding="utf-8-sig")

    now = dt.datetime.now()
    sys_rows = [
        (now - dt.timedelta(hours=1), "INFO", "데이터수신", "신규 영상 2건 수신 완료 (SAR 1, EO 1)"),
        (now - dt.timedelta(hours=2), "INFO", "분석엔진", "객체식별 배치 작업 정상 종료"),
        (now - dt.timedelta(hours=3), "WARN", "분석엔진", "GPU 메모리 사용률 87% — 임계치 근접"),
        (now - dt.timedelta(hours=5), "INFO", "인증", "비밀번호 5회 오류 계정 잠금 해제 처리"),
        (now - dt.timedelta(hours=8), "INFO", "DB", "분석 로그 테이블 백업 완료"),
        (now - dt.timedelta(days=1, hours=2), "ERROR", "데이터수신", "수신 채널 응답 지연 — 재시도 후 정상화"),
        (now - dt.timedelta(days=1, hours=4), "INFO", "스케줄러", "야간 정기 지역탐지 스캔 완료"),
        (now - dt.timedelta(days=1, hours=6), "INFO", "분석엔진", "SAR 식별 모델 v2.1 로드 완료"),
        (now - dt.timedelta(days=2, hours=1), "WARN", "DB", "디스크 사용률 75% 초과"),
        (now - dt.timedelta(days=2, hours=3), "INFO", "인증", "신규 계정 1건 생성"),
    ]
    pd.DataFrame(
        [{"일시": f"{t:%Y-%m-%d %H:%M}", "수준": lv, "모듈": m, "내용": msg} for t, lv, m, msg in sys_rows]
    ).to_csv(DATA_DIR / "system_log.csv", index=False, encoding="utf-8-sig")

    login_rows = [
        {"일시": f"{now - dt.timedelta(days=1, hours=9):%Y-%m-%d %H:%M}", "아이디": "user", "성명": "김OO", "역할": "영상판독관", "결과": "성공"},
        {"일시": f"{now - dt.timedelta(days=1, hours=8):%Y-%m-%d %H:%M}", "아이디": "cmd", "성명": "최OO", "역할": "지휘관", "결과": "성공"},
        {"일시": f"{now - dt.timedelta(days=1, hours=2):%Y-%m-%d %H:%M}", "아이디": "user", "성명": "-", "역할": "-", "결과": "실패(비밀번호 오류)"},
    ]
    pd.DataFrame(login_rows).to_csv(DATA_DIR / "login_history.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    for sensor in SENSORS:
        for folder in FOLDERS:
            (IMG_DIR / sensor / folder).mkdir(parents=True, exist_ok=True)
        (XAI_DIR / sensor).mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    font = get_font(17)
    all_dets: list[dict] = []
    all_regions: list[dict] = []
    all_scenes: dict[str, list[str]] = {}
    for sensor in SENSORS:
        all_scenes[sensor] = scene_names(sensor)
        prev_dets: list[dict] = []
        for scene in all_scenes[sensor]:
            time_tok = scene.split("_")[3]
            dets = (make_detections(sensor, scene) if time_tok == TIMES[0]
                    else derive_next(sensor, scene, prev_dets))
            prev_dets = dets
            all_dets.extend(dets)
            base = sar_base(scene, dets) if sensor == "SAR" else eo_base(scene, dets)
            base.save(IMG_DIR / sensor / "원본" / f"{scene}.png")
            region_image(base, dets, font).save(IMG_DIR / sensor / "지역탐지" / f"{scene}.png")
            object_image(base, dets, font).save(IMG_DIR / sensor / "객체식별" / f"{scene}.png")
            cam = gradcam_image(base, dets)
            cam.save(XAI_DIR / sensor / f"{scene}.png")
            # 신뢰성 검토용 결합 뷰: 히트맵 + 탐지 박스
            draw_boxes(cam.copy(), dets, font).save(XAI_DIR / sensor / f"{scene}_boxes.png")

            x1, y1, x2, y2 = region_bbox(dets)
            all_regions.append({
                "파일명": scene, "센서": sensor, "구역ID": "R-1",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "신뢰도": max(r["신뢰도"] for r in dets),
                "후보표적수": len(dets),
                "중심위도": round(sum(r["위도"] for r in dets) / len(dets), 5),
                "중심경도": round(sum(r["경도"] for r in dets) / len(dets), 5),
            })

    det_df = pd.DataFrame(all_dets)
    det_df.to_csv(DATA_DIR / "detections.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(all_regions).to_csv(DATA_DIR / "regions.csv", index=False, encoding="utf-8-sig")
    make_logs(all_scenes, det_df)
    make_logo()
    print(f"더미 데이터 생성 완료: {DATA_DIR}")


if __name__ == "__main__":
    main()
