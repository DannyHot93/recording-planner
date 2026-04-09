# Recording Planner

방송 녹화 일정을 정리하고, 이미지(OCR) 또는 JSON 입력으로 갱신한 뒤 정적 웹 페이지로 보여 주는 저장소입니다. `main` 브랜치에 푸시하면 GitHub Pages에 `web-output` 내용이 배포됩니다.

## 구성

| 경로 | 설명 |
|------|------|
| `data/schedule.json` | 구조화된 일정 데이터 (프로그램명, 녹화일·시간, 장소, 메모 등) |
| `incoming/latest_schedule.json` | 외부에서 넣는 최신 일정 페이로드 (`watch_and_update.py`가 감시) |
| `parsed/*.json` | OCR 등으로 추출한 녹화 의뢰 단위 레코드 |
| `media/` | 처리된 이미지; `media/inbound/`에 넣으면 인바운드 파이프라인이 소비 |
| `web-output/` | 공개 사이트용 `index.html`, `data.json` (Pages 배포 소스) |
| `docs/` | `update_schedule.py`가 생성하는 HTML (스케줄 JSON 기반 흐름) |
| `Recordingplanner/` | 날짜별 녹화 의뢰서 마크다운 등 문서 산출물 |
| `scripts/` | 처리·생성 스크립트 |

## 요구 사항

- Python 3.x  
- 공통: `python-dateutil`, `jinja2` (주간 HTML 생성 등)  
- 인바운드 이미지 처리: Tesseract CLI (`tesseract`) 또는 `Pillow` + `pytesseract`  
- 타임존: 스크립트는 기본적으로 `Asia/Seoul`을 사용합니다.

```bash
pip install python-dateutil jinja2
# 이미지 OCR (선택)
pip install Pillow pytesseract
```

## 주요 스크립트

### 1. JSON 일정 갱신 → HTML + (선택) 푸시

`data/schedule.json`을 읽고 갱신한 뒤 `docs/index.html`을 만듭니다.

```bash
python3 scripts/update_schedule.py incoming/latest_schedule.json
```

### 2. 인바운드 이미지 → OCR → 파싱 → 사이트 재생성

`media/inbound/`에 이미지를 두고 실행합니다. 파일을 `media/`로 옮기고, OCR로 날짜를 찾아 `parsed/*.json`을 만든 뒤 `regenerate_all_future.py`(실패 시 `generate_weekly.py`)를 호출하고, 변경을 커밋·푸시하려고 시도합니다.

```bash
python3 scripts/process_inbound.py
```

### 3. 파싱 결과만으로 공개 페이지 재생성

`parsed/`의 미래 일정만 반영해 `web-output/index.html`, `web-output/data.json` 및 저장소 루트의 `index.html`·`data.json`을 갱신합니다.

```bash
python3 scripts/regenerate_all_future.py
```

### 4. `incoming` 감시 (로컬)

`incoming/latest_schedule.json`이 바뀌면 `update_schedule.py`를 실행합니다.

```bash
python3 scripts/watch_and_update.py
```

### 5. 오래된 파싱/미디어 정리

7일보다 오래된 항목을 백업 쪽으로 옮깁니다. CI에서도 주기적으로 실행됩니다.

```bash
python3 scripts/cleanup_old_parsed.py --days 7
```

## 배포 (GitHub Pages)

- 워크플로: `.github/workflows/pages.yml` — `main`에 푸시 시 `web-output/`을 `public/`으로 복사해 Pages에 게시합니다.
- 정리 작업: `.github/workflows/cleanup-parsed.yml` — 매일 UTC 18:00(한국 시간 새벽 3시대)에 오래된 `parsed`/`media` 정리 후 커밋·푸시합니다.

저장소 설정에서 Pages 소스가 이 워크플로에 맞게 되어 있는지 확인하세요.

## 스킬 패키지

같은 파이프라인을 다른 환경에 옮길 때는 `skills/recording-pipeline-skill/`의 설명과 `install.sh`를 참고하면 됩니다.

## 라이선스

저장소에 `LICENSE` 파일이 없다면 필요 시 추가하세요.
