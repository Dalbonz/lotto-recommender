"""
연금복권720+ 당첨번호 자동 업데이트.

로또 6/45와 달리 동행복권은 연금복권720+에 대한 공식 JSON API를 공개하고 있지 않다.
그래서 공개 결과 페이지(HTML)를 받아 텍스트에서 패턴으로 추출하는 방식을 쓴다.

주의(정직하게 밝힘): 이 스크립트를 작성한 환경(샌드박스)에서는 dhlottery.co.kr 접속 자체가
네트워크 정책으로 막혀 있어서, 실제 페이지의 HTML 구조를 직접 눈으로 확인하지 못한 채
합리적으로 추정되는 패턴으로 작성했다. GitHub Actions에서 처음 실행될 때 파싱이 실패할 수
있으므로, 검증에 실패하면 데이터를 절대 덮어쓰지 않고 로그만 남기고 조용히 종료한다.
(로또 6/45 쪽은 공식 JSON API를 쓰므로 이 문제가 없다.)
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "pension720.json"
RESULT_URL = "https://www.dhlottery.co.kr/gameResult.do?method=win720&drwNo={round}"

GROUP_NUM_RE = re.compile(r"([1-5])\s*조[^0-9]{0,30}?(\d{6})")
ROUND_RE = re.compile(r"(\d{1,4})\s*회")
DATE_RE = re.compile(r"(\d{4})[.\-년]\s*(\d{1,2})[.\-월]\s*(\d{1,2})")


def strip_tags(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_existing() -> list:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def fetch_round(round_no: int) -> dict | None:
    req = urllib.request.Request(
        RESULT_URL.format(round=round_no),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("euc-kr", errors="ignore")

    text = strip_tags(raw)

    # 존재하지 않는 회차인지 대략 판단 (본문이 지나치게 짧거나 "없습니다" 류 안내문)
    if len(text) < 200 or "없습니다" in text[:400]:
        return None

    groups = {}
    for m in GROUP_NUM_RE.finditer(text):
        g = int(m.group(1))
        num = m.group(2)
        groups.setdefault(g, num)

    round_match = ROUND_RE.search(text)
    date_match = DATE_RE.search(text)

    if len(groups) != 5:
        raise ValueError(
            f"조 번호 5개를 모두 찾지 못함 (찾은 개수: {len(groups)}) - 페이지 구조가 예상과 다를 수 있음"
        )

    return {
        "round": round_no,
        "date": (
            f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
            if date_match else None
        ),
        "groups": [groups[g] for g in range(1, 6)],  # index 0 = 1조 ... index 4 = 5조
    }


def main():
    existing = load_existing()
    last_round = existing[-1]["round"] if existing else 0
    print(f"[win720] 현재 저장된 마지막 회차: {last_round}")

    round_no = last_round + 1
    new_rows = []
    failed = False
    while True:
        try:
            row = fetch_round(round_no)
        except Exception as e:
            print(f"[win720] {round_no}회 파싱 실패, 건너뜀: {e}", file=sys.stderr)
            failed = True
            break
        if row is None:
            break
        new_rows.append(row)
        print(f"[win720] {round_no}회 ({row['date']}) 수신: {row['groups']}")
        round_no += 1
        time.sleep(0.3)

    if new_rows:
        existing.extend(new_rows)
        DATA_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"[win720] {len(new_rows)}개 회차 추가 저장 (최신 {existing[-1]['round']}회)")
    else:
        print("[win720] 새로 저장된 회차 없음")

    if failed:
        print(
            "[win720] 경고: 파싱 실패가 감지되었습니다. "
            "페이지 구조가 바뀌었을 수 있으니 scripts/fetch_win720.py 점검이 필요합니다.",
            file=sys.stderr,
        )
        # 워크플로우 전체를 실패시키지는 않음 (로또 데이터는 정상 커밋되도록)


if __name__ == "__main__":
    main()
