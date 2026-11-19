"""
로또 6/45 당첨번호 자동 업데이트.

동행복권이 2026년에 사이트를 SPA(자바스크립트 렌더링)로 개편하면서 예전에 쓰던
`common.do?method=getLottoNumber&drwNo=N` 은 폐기됐다. 그 URL은 이제 JSON 대신
302로 홈페이지 HTML을 돌려주기 때문에, 이 스크립트는 몇 달 동안 매 실행마다
파싱에 실패하면서도 "새 회차 없음"처럼 조용히 지나갔다(1205회부터 누락).

그래서 결과 화면(`/lt645/result`)이 실제로 호출하는 JSON 엔드포인트를 직접 쓴다:

    GET https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do?srchLtEpsd={회차}

응답(200, application/json):
    {"data": {"list": [
        {"ltEpsd": 1250, "tm1WnNo": 1, ..., "tm6WnNo": 28, "bnsWnNo": 8,
         "ltRflYmd": "20261114", ...}, ...
    ]}}

- 요청 회차를 중심으로 최대 10회차(요청-5 ~ 요청+4)를 내려준다.
- 요청 회차가 아직 추첨되지 않았으면 `list`가 빈 배열로 온다(그게 "다음 회차 없음").
- 쿠키나 리퍼러 없이 호출된다. (같은 형제 엔드포인트 `/pt720/selectPstPt720WnList.do`를
  쓰는 `fetch_win720.py`도 GitHub Actions 러너에서 정상 동작 중이다.)

조회·파싱 자체가 실패하면 재시도 후 **exit 1** 로 끝나 워크플로가 빨갛게 보이게 한다.
"아직 추첨되지 않음"과 "가져오지 못함"을 구분하는 것이 이 스크립트의 핵심이다.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "lotto645.json"
META_PATH = Path(__file__).resolve().parent.parent / "data" / "updated.json"
API_URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do?srchLtEpsd={round}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class FetchError(RuntimeError):
    """조회 실패(네트워크/HTTP/파싱). "아직 추첨 안 됨"과는 다른 상태."""


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


def _to_row(item: dict) -> dict:
    """API 항목 하나를 저장 포맷으로 바꾸고 값이 말이 되는지 검사한다."""
    try:
        rnd = int(item["ltEpsd"])
        numbers = sorted(int(item[f"tm{i}WnNo"]) for i in range(1, 7))
        bonus = int(item["bnsWnNo"])
        ymd = str(item["ltRflYmd"])
    except (KeyError, TypeError, ValueError) as e:
        raise FetchError(f"응답 항목에 필요한 값이 없거나 형식이 다름: {item!r} ({e})") from e

    if len(ymd) != 8 or not ymd.isdigit():
        raise FetchError(f"{rnd}회 날짜 형식이 예상과 다름: {ymd!r}")
    date = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"

    if len(set(numbers)) != 6 or not all(1 <= n <= 45 for n in numbers):
        raise FetchError(f"{rnd}회 당첨번호가 이상함: {numbers}")
    if not 1 <= bonus <= 45:
        raise FetchError(f"{rnd}회 보너스번호가 이상함: {bonus}")

    return {"round": rnd, "date": date, "numbers": numbers, "bonus": bonus}


def fetch_window(round_no: int, retries: int = 3) -> list:
    """요청 회차 주변의 회차 목록을 가져온다. 실패하면 FetchError."""
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(API_URL.format(round=round_no), headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
            items = payload["data"]["list"]
            if not isinstance(items, list):
                raise ValueError(f"list 가 배열이 아님: {type(items)}")
            return items
        except Exception as e:  # HTTP/네트워크/JSON/구조 오류를 모두 포함
            last_err = e
            if attempt < retries:
                time.sleep(2.0 * attempt)
                continue
            raise FetchError(
                f"{round_no}회 조회 실패 — {retries}회 재시도 후에도 유효한 응답을 받지 못함 "
                f"(마지막 오류: {type(e).__name__}: {e})"
            ) from e
    raise FetchError(f"{round_no}회 조회 실패 (마지막 오류: {last_err})")


def get_draw(round_no: int):
    """해당 회차를 반환한다. 아직 추첨되지 않았으면 None, 조회 실패면 FetchError."""
    items = fetch_window(round_no)
    for item in items:
        if int(item.get("ltEpsd", -1)) == round_no:
            return _to_row(item)
    rounds = [int(i.get("ltEpsd", 0)) for i in items]
    if rounds and max(rounds) < round_no:
        # 창이 최신 회차에서 잘린 경우 = 요청 회차는 아직 추첨되지 않음
        return None
    if rounds:
        raise FetchError(
            f"{round_no}회를 요청했는데 응답에 없고 더 최신 회차는 있음 "
            f"(받은 회차: {sorted(rounds)}). API 응답 형식이 바뀌었는지 확인 필요."
        )
    # 빈 배열 = 요청 회차가 아직 추첨되지 않음
    return None


def main() -> int:
    existing = load_existing()
    last_round = existing[-1]["round"] if existing else 0
    print(f"[lotto645] 현재 저장된 마지막 회차: {last_round}")

    new_rows = []
    round_no = last_round + 1
    try:
        while True:
            row = get_draw(round_no)
            if row is None:
                print(f"[lotto645] {round_no}회는 아직 추첨되지 않음 (이미 최신)")
                break
            new_rows.append(row)
            print(f"[lotto645] {round_no}회 ({row['date']}) 수신")
            round_no += 1
            time.sleep(0.3)
    except FetchError as e:
        # 일부라도 받았으면 저장은 해 둔다(다음 실행이 이어받도록).
        if new_rows:
            existing.extend(new_rows)
            DATA_PATH.write_text(
                json.dumps(existing, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        print(f"[lotto645] 오류: {e}", file=sys.stderr)
        print(
            "[lotto645] 조회에 실패했습니다. '새 회차 없음'이 아니라 '확인하지 못함' 상태이므로 "
            "워크플로를 실패로 끝냅니다.",
            file=sys.stderr,
        )
        return 1

    if new_rows:
        existing.extend(new_rows)
        DATA_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"[lotto645] {len(new_rows)}개 회차 추가 저장 (최신 {existing[-1]['round']}회)")
    else:
        print("[lotto645] 새 회차 없음 (이미 최신)")

    touch_updated("lotto645")
    return 0


if __name__ == "__main__":
    sys.exit(main())
