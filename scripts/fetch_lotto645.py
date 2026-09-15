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


def fetch_round(round_no: int, retries: int = 3) -> dict | None:
    """1회차를 조회한다. 네트워크/파싱 오류는 일시적일 수 있으므로 재시도하고,
    재시도를 모두 소진해도 실패하면 예외를 던진다(= "이 회차가 아직 없다"와는
    구분되는 상태). 서버가 정상 JSON으로 실패를 응답한 경우에만 None을 반환한다
    ("아직 추첨되지 않은 회차"라는 뜻).

    이전 버전은 이 두 경우(진짜로 다음 회차가 없음 vs. 요청 자체가 실패함)를
    구분하지 않고 모든 예외를 "다음 회차 없음"으로 취급했다 — 그래서 API가
    빈 응답(공백만 있는 응답)을 반환하는 문제가 생겨도 조용히 "새 회차 없음"으로
    잘못 보고되고, 실제로는 몇 달치 회차가 누락되는데도 알아챌 방법이 없었다.
    """
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            API_URL.format(round=round_no),
            headers={
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(
                f"{retries}회 재시도했지만 유효한 응답을 받지 못함 (마지막 오류: {e})"
            ) from e
        else:
            break

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
    fetch_failed = False
    while True:
        try:
            row = fetch_round(round_no)
        except Exception as e:
            # 이 회차가 "아직 없어서"가 아니라 요청 자체가 실패한 것이므로,
            # "새 회차 없음"과 혼동되지 않도록 명확히 오류로 로그를 남긴다.
            print(f"[lotto645] {round_no}회 조회 실패(네트워크/파싱 오류): {e}", file=sys.stderr)
            fetch_failed = True
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
        if fetch_failed:
            print(
                f"[lotto645] {round_no}회부터는 조회가 실패해서 중단함 "
                "(더 새 회차가 있는지는 다음 실행에서 재확인됨)",
                file=sys.stderr,
            )
    elif fetch_failed:
        print(
            "[lotto645] 회차 조회가 실패해서 최신 여부를 확인하지 못함 "
            "(진짜로 새 회차가 없는 것인지 알 수 없음 — 다음 실행에서 재시도됨)",
            file=sys.stderr,
        )
    else:
        print("[lotto645] 새 회차 없음 (이미 최신)")

    # 새 회차를 하나도 못 구한 채로 조회 자체가 실패한 경우에만 "확인 시각"을
    # 갱신하지 않는다 — 갱신해버리면 실제로는 최신 여부를 확인하지 못했는데도
    # 확인된 것처럼 보이게 되기 때문이다. 일부라도 새 회차를 저장했다면(부분
    # 성공) 그 시점까지는 실제로 갱신됐으므로 시각을 남긴다.
    if new_rows or not fetch_failed:
        touch_updated("lotto645")


if __name__ == "__main__":
    main()
