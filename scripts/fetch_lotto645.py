"""
로또 6/45 당첨번호 자동 업데이트.
동행복권 공식 조회 API(common.do?method=getLottoNumber)를 사용한다.
이 API는 비공식적으로 널리 쓰이는 공개 엔드포인트로, 별도 인증(API 키) 없이 무료로 호출 가능하다.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "lotto645.json"
META_PATH = Path(__file__).resolve().parent.parent / "data" / "updated.json"
API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={round}"


def touch_updated(key: str):
    meta = {}
    if META_PATH.exists():
        try:
            meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    meta[key] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def load_existing() -> list:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def fetch_round(round_no: int) -> dict | None:
    req = urllib.request.Request(
        API_URL.format(round=round_no),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("returnValue") != "success":
        return None
    return {
        "round": data["drwNo"],
        "date": data["drwNoDate"],
        "numbers": sorted(
            [data["drwtNo1"], data["drwtNo2"], data["drwtNo3"],
             data["drwtNo4"], data["drwtNo5"], data["drwtNo6"]]
        ),
        "bonus": data["bnusNo"],
    }


def main():
    existing = load_existing()
    last_round = existing[-1]["round"] if existing else 0
    print(f"[lotto645] 현재 저장된 마지막 회차: {last_round}")

    round_no = last_round + 1
    new_rows = []
    while True:
        try:
            row = fetch_round(round_no)
        except Exception as e:
            print(f"[lotto645] {round_no}회 조회 중 오류: {e}", file=sys.stderr)
            break
        if row is None:
            break
        new_rows.append(row)
        print(f"[lotto645] {round_no}회 ({row['date']}) 수신")
        round_no += 1
        time.sleep(0.3)

    if new_rows:
        existing.extend(new_rows)
        DATA_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"[lotto645] {len(new_rows)}개 회차 추가 저장 (최신 {existing[-1]['round']}회)")
    else:
        print("[lotto645] 새 회차 없음 (이미 최신)")

    # 새 회차가 없어도 API 조회 자체는 성공했으므로 "마지막 확인 시각"을 갱신한다.
    touch_updated("lotto645")


if __name__ == "__main__":
    main()
