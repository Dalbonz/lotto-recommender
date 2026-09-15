"""
연금복권720+ 당첨번호 자동 업데이트.

예전 버전은 동행복권이 공식 API를 공개하지 않는다고 보고 결과 페이지(HTML)를 받아
정규식으로 파싱했는데, 실제로 Codespace에서 직접 페이지를 열어 보니 두 가지가
잘못돼 있었다.

1. 예전에 쓰던 `gameResult.do?method=win720&drwNo=N` URL은 더 이상 당첨번호를
   담고 있지 않다. 동행복권이 결과 페이지를 SPA(자바스크립트 렌더링)로 바꾸면서
   그 URL은 빈 페이지 껍데기만 반환한다 — 그래서 정규식이 항상 0개 매칭이었다.
   SPA가 내부적으로 호출하는 JSON API(`/pt720/selectPstPt720WnList.do`)를 대신
   직접 호출한다. 이 API는 한 번의 요청으로 1회차부터 최신 회차까지 전체 이력을
   반환하므로, 로또처럼 회차별로 반복 요청할 필요도 없다.
2. **데이터 모델 자체가 잘못돼 있었다.** 연금복권720+는 "5개 조가 각각 당첨번호를
   가진다"가 아니라, 회차마다 1등은 특정 조(1~5) 하나 + 6자리 번호 하나뿐이고,
   보너스 6자리 번호가 조 상관없이 별도로 하나 더 있는 구조다. 그래서
   `data/pension720.json`의 스키마를 `groups: [5개 번호]`에서
   `group + number + bonusNumber`로 바꿨다(index.html의 통계 계산도 함께 수정).
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "pension720.json"
META_PATH = Path(__file__).resolve().parent.parent / "data" / "updated.json"
API_URL = "https://www.dhlottery.co.kr/pt720/selectPstPt720WnList.do"


def touch_updated(key: str):
    meta = {}
    if META_PATH.exists():
        try:
            meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    meta[key] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def fetch_all_rounds() -> list[dict]:
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    rows = payload["data"]["result"]
    out = []
    for row in rows:
        ymd = str(row["psltRflYmd"])
        out.append({
            "round": int(row["psltEpsd"]),
            "date": f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}",
            "group": int(row["wnBndNo"]),
            "number": str(row["wnRnkVl"]).zfill(6),
            "bonusNumber": str(row["bnsRnkVl"]).zfill(6),
        })
    out.sort(key=lambda r: r["round"])
    return out


def load_existing() -> list:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def main():
    existing = load_existing()
    last_round = existing[-1]["round"] if existing else 0
    print(f"[win720] 현재 저장된 마지막 회차: {last_round}")

    try:
        all_rounds = fetch_all_rounds()
    except Exception as e:
        print(f"[win720] API 조회 실패, 건너뜀: {e}", file=sys.stderr)
        return

    # API 조회 자체는 성공했으므로 "마지막 확인 시각"을 갱신한다.
    touch_updated("pension720")

    new_rows = [r for r in all_rounds if r["round"] > last_round]
    if not new_rows:
        print("[win720] 새로 저장된 회차 없음")
        return

    existing.extend(new_rows)
    existing.sort(key=lambda r: r["round"])
    DATA_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"[win720] {len(new_rows)}개 회차 추가 저장 (최신 {existing[-1]['round']}회, {existing[-1]['date']})")


if __name__ == "__main__":
    main()
