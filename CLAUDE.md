# 프로젝트 컨텍스트 (이전 세션에서 인계)

이 파일은 다른 환경(Claude Code on the web)에서 작업하던 걸 Codespace로 넘기면서
새 세션이 맥락을 이어받도록 남긴 것이다. 사용자는 한국어로 소통하며, 간결하고
정직한 답변을 선호한다. 검증 안 된 걸 됐다고 말하지 말 것 — 특히 자동화가
"작동한다"는 주장은 실제 Actions 로그로 확인 전에는 하지 말 것.

## 프로젝트가 뭔지

로또 6/45 + 연금복권720+ 당첨번호를 분석해서 번호를 추천하는 정적 웹앱.
- GitHub Actions가 매일 자동으로 최신 당첨번호를 수집
- GitHub Pages로 무료 배포 (`https://dalbonz.github.io/lotto-recommender/`)
- 설치 없이 브라우저로 여는 PWA (홈 화면 추가 가능)

**중요한 전제(항상 사용자에게 고지)**: 복권은 매회 독립 무작위 추첨이라 과거 데이터가
다음 회차 확률에 영향을 주지 않는다. 추천 기능은 재미/참고용이지 확률을 높이지 않는다.

## 지금까지 온 경로 (왜 이렇게 됐는지)

1. 처음엔 사용자가 "로컬 앱"을 요청 → Python CLI + 로컬 서버로 과하게 복잡하게 만듦 (실수, 사용자가 지적함)
2. 사용자가 폰(안드로이드, Acode 에디터)에서 쓰는 걸 알게 됨 → 정적 HTML 한 장으로 재구성,
   claude.ai 아티팩트로 배포 (`https://claude.ai/code/artifact/4ff4da3f-19e1-4c5f-9ff5-9a5c7e3e1316`,
   **지금은 구버전, 이 저장소가 최신**)
3. "한 달 뒤에도 데이터가 자동으로 쌓이나?" 질문 → 아티팩트는 정적이라 안 쌓인다고 정직하게 답함
4. 사용자가 "GitHub + 무료 API로 진짜 자동 업데이트 + 연금복권도 + UI 개선(Apple 스타일)" 요청
5. 이 저장소(`Dalbonz/lotto-recommender`)를 만들어 현재 구조로 구축, push 완료
6. GitHub Pages 활성화(Settings → Pages → Source: GitHub Actions) 완료
7. **버그 발견 및 수정**: `GITHUB_TOKEN`으로 푸시한 커밋은 다른 워크플로우의 push 트리거를
   연쇄 실행 안 시키는 GitHub 정책 때문에, 데이터 업데이트가 성공해도 사이트가 재배포 안
   되는 문제가 있었음 → `update-data.yml`이 데이터 커밋 후 자체적으로 Pages 배포까지
   하도록 수정함 (커밋 `c50595f`)
8. **여기서 인계됨**: 수정된 워크플로우를 아직 실제로 수동 실행(Run workflow)해서
   검증하지 못한 상태. 이게 다음 세션이 먼저 확인해야 할 일.

## 구조

```
index.html                     # 메인 앱 (Apple 스타일, 로또/연금복권 세그먼트 탭)
manifest.json, sw.js, icons/   # PWA
data/lotto645.json             # 로또 1~1204회 시드 데이터 포함 (2025-12-27 기준)
data/pension720.json           # 빈 배열 []  — 첫 자동 업데이트 실행 시 1회부터 백필됨
scripts/fetch_lotto645.py      # 동행복권 공식 공개 JSON API 사용 (키 불필요, 검증된 방식)
scripts/fetch_win720.py        # 공식 API 없음 → 결과 페이지 HTML 텍스트 패턴 파싱 (추정 기반, 미검증)
.github/workflows/update-data.yml   # 매일 UTC13:00(KST22:00) + 수동실행. 데이터 수집 후 자체 배포까지 함
.github/workflows/deploy-pages.yml  # main에 push되면 배포 (코드만 바뀔 때용, 데이터 워크플로우와 중복 가능)
```

## 알려진 리스크 / 정직하게 밝혀둘 것

- **`fetch_win720.py`는 눈으로 실제 페이지를 보고 검증하지 못한 채 작성됨.** 이전 세션이
  작업한 샌드박스 환경은 dhlottery.co.kr 접속 자체가 네트워크 정책으로 차단되어 있어서,
  실제 HTML 구조를 확인할 방법이 없었다. Codespace는 일반 인터넷 접속이 되니, 여기서
  `python3 scripts/fetch_win720.py`를 직접 돌려보고 실패하면 그 자리에서 실제 구조를
  보고 고칠 수 있다 — 이게 우선순위 높은 작업.
- `fetch_lotto645.py`가 쓰는 API(`common.do?method=getLottoNumber`)는 커뮤니티에 널리
  검증된 공개 엔드포인트이지만, 이 프로젝트에서 GitHub Actions 러너로 실제 호출 성공한
  걸 직접 로그로 확인한 적은 아직 없다(위 7번 버그 수정 이후 재실행 대기 중).
- dhlottery가 클라우드/데이터센터 IP 대역(GitHub Actions 러너 등)을 차단할 가능성은
  낮지만 아직 배제 못함 — 실패하면 이것도 원인 후보.
- GitHub Actions의 스케줄 cron은 정시 보장이 아니라 몇십 분~몇 시간 지연 가능.

## 다음에 할 일 (우선순위)

1. Actions 탭에서 "당첨번호 자동 업데이트" 워크플로우를 수동 실행(Run workflow)하고 로그 확인
2. `[lotto645]` 로그에서 1204회 이후 새 회차가 실제로 잡히는지 확인
3. `[win720]` 로그 확인 — 실패하면 Codespace 터미널에서 직접
   `curl -s "https://www.dhlottery.co.kr/gameResult.do?method=win720&drwNo=1"` 등으로
   실제 페이지를 보고 `scripts/fetch_win720.py`의 정규식(`GROUP_NUM_RE` 등)을 실제 구조에
   맞게 고칠 것
4. 사이트(`https://dalbonz.github.io/lotto-recommender/`)에서 최신 회차와 연금복권 통계가
   실제로 채워지는지 확인
