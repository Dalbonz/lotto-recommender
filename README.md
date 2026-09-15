# 복권 번호 추천기

로또 6/45, 연금복권720+ 당첨번호를 분석해서 번호를 추천하는 정적 웹앱.
GitHub Actions가 매주 목요일·토요일 당첨 발표 직후 자동으로 최신 당첨번호를 수집해서 저장하고, GitHub Pages로 배포된다.

## ⚠️ 먼저 읽어주세요

복권 추첨은 회차마다 완전히 독립적인 무작위 추첨입니다. 과거 당첨번호의 빈도나 패턴은
**다음 회차의 당첨 확률에 전혀 영향을 주지 않습니다.** 이 앱의 추천 번호는 당첨 확률을
높이지 않으며, 과거 데이터를 참고하는 재미 요소일 뿐입니다.

## 구조

```
.
├── index.html                  # 메인 앱 (로또/연금복권 탭)
├── manifest.json, sw.js        # PWA (홈 화면 설치, 오프라인 캐싱)
├── icons/                      # PWA 아이콘
├── data/
│   ├── lotto645.json           # 로또 6/45 회차별 당첨번호
│   └── pension720.json         # 연금복권720+ 회차별 당첨번호
├── scripts/
│   ├── fetch_lotto645.py       # 동행복권 공식 JSON API로 로또 수집
│   └── fetch_win720.py         # 연금복권720+ 내부 JSON API(selectPstPt720WnList.do)로 수집
└── .github/workflows/
    ├── update-data.yml         # 매주 목·토 추첨 직후 자동 실행: 당첨번호 수집 → 커밋
    └── deploy-pages.yml        # main 브랜치 push 시 GitHub Pages 배포
```

## 자동 업데이트는 어떻게 동작하나

- `update-data.yml`이 매주 두 번, 각 당첨 발표 직후 GitHub Actions에서 실행됩니다.
  - 연금복권720+ (목요일 18:35 KST 추첨) → 19:00 KST(UTC 10:00)
  - 로또 6/45 (토요일 20:35 KST 추첨) → 21:00 KST(UTC 12:00)
  - 두 실행 모두 로또·연금복권 스크립트를 함께 돌리므로(이미 최신 회차면 아무것도 하지 않고 건너뜀),
    추첨 발표가 예정보다 늦어져도 다음 실행이나 수동 실행(`workflow_dispatch`)으로 보완할 수 있습니다.
- 로또 6/45는 동행복권이 공개한 JSON 조회 API(`common.do?method=getLottoNumber`)를 사용합니다.
  이 API는 별도 키 없이 무료로 쓸 수 있는, 널리 알려진 공개 엔드포인트입니다.
- 연금복권720+는 결과 페이지가 자바스크립트로 그려지는 SPA라 정적 HTML만 받아서는
  당첨번호를 알 수 없습니다. 대신 그 페이지가 내부적으로 호출하는 JSON API
  (`/pt720/selectPstPt720WnList.do`)를 직접 호출합니다 — 별도 키 없이 1회 요청으로
  1회차부터 최신 회차까지 전체 이력을 돌려주는 비공식 엔드포인트입니다. 호출이
  실패하면 기존 데이터를 덮어쓰지 않고 조용히 건너뛰도록 만들어뒀습니다
  (Actions 로그에서 `[win720]` 경고로 확인 가능). 동행복권이 이 API를 바꾸면 다시
  깨질 수 있습니다.
- 연금복권720+는 회차마다 1등이 특정 조(1~5) 하나 + 6자리 번호 하나뿐이고, 보너스
  6자리 번호가 조 상관없이 하나 더 있는 구조입니다(`data/pension720.json`의
  `group`/`number`/`bonusNumber` 필드).
- 새 회차가 있으면 `data/*.json`을 갱신하고 자동으로 커밋·푸시합니다.
- 커밋이 발생하면 `deploy-pages.yml`이 이어서 실행되어 최신 데이터로 사이트를 다시 배포합니다.

## GitHub Pages 활성화 (최초 1회, 수동)

1. 저장소 **Settings → Pages**로 이동
2. **Source**를 **GitHub Actions**로 선택 후 저장
3. `main` 브랜치에 push되면 `deploy-pages.yml`이 자동으로 사이트를 배포합니다
4. 배포 후 URL은 `https://<계정명>.github.io/<저장소명>/` 형태입니다

## 로컬에서 미리 보기

```bash
python3 -m http.server 8000
# http://localhost:8000 접속
```

(로컬 `python3 -m http.server`는 `fetch()`가 정상 동작하도록 하기 위한 것으로, `index.html`을
파일로 직접 더블클릭해서 열면 데이터가 안 보일 수 있습니다.)

## 데이터 출처

동행복권(dhlottery.co.kr) 공개 결과 정보 기반.
