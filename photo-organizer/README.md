# photo-organizer

Galaxy와 iPhone에서 찍은 사진이 Google Drive와 네이버 클라우드에 나뉘어 백업되면서, 실제 촬영
순서대로 정리/탐색하기 어려운 문제를 해결하는 로컬 CLI 도구입니다. EXIF, 파일명 규칙(Galaxy,
카카오톡, 스크린샷, WhatsApp 등), Google Drive 메타데이터, 파일시스템 수정시각을 순서대로
시도해서 각 사진의 실제 촬영 시각을 판별하고, 두 기기의 사진을 하루 단위로 실제 시간순으로
섞어 정리합니다. 신뢰할 수 있는 날짜를 찾지 못한 사진은 자동으로 정리하지 않고 검토 폴더로
따로 모아둡니다.

블로그 포스팅 자동화 자체와는 연동하지 않습니다 — 이 도구는 사진 정리까지만 담당합니다.

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 최초 1회 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 **Google
   Drive API**를 활성화합니다.
2. OAuth 동의 화면(External, Testing 상태로 충분)을 만들고 본인 Google 계정을 테스트 사용자로
   추가합니다.
3. 사용자 인증 정보 → OAuth 클라이언트 ID 생성 → 애플리케이션 유형 **데스크톱 앱**을 선택하고
   JSON을 다운로드해 `credentials/credentials.json`으로 저장합니다. (기본 위치는
   `config.yaml`의 `credentials_dir`로 바뀔 수 있습니다.)
4. `config.example.yaml`을 `config.yaml`로 복사한 뒤 다음을 채웁니다.
   - `drive_source_folders`: Galaxy/iPhone이 백업되는 Drive 폴더 ID와 `device_hint`
   - `naver_inbox_dir`: 네이버 클라우드에서 수동으로 다운로드한 사진을 넣어둘 로컬 폴더
   - `library_root`, `review_root`, `state_dir`, `raw_cache_dir`, `credentials_dir`
5. 최초 브라우저 인증: `python organize_photos.py auth --config config.yaml`

## 사용법

```bash
# 미리보기 (아무 것도 쓰지 않음)
python organize_photos.py run --config config.yaml --dry-run

# 실제 정리 실행 (Drive 동기화 + 네이버 인박스 스캔)
python organize_photos.py run --config config.yaml

# 특정 소스만
python organize_photos.py run --config config.yaml --source naver
python organize_photos.py run --config config.yaml --source drive

# 검토 대기 중인 사진 목록
python organize_photos.py review list --config config.yaml

# 검토 대기 사진에 날짜를 수동으로 확정하고 library/로 승격
python organize_photos.py review resolve --config config.yaml \
    --sha256 <해시> --date "2024-01-01 10:00:00"

# 요약
python organize_photos.py status --config config.yaml
```

`--config`는 서브커맨드 앞/뒤 어디에 와도 동작합니다.

## 동작 원칙 (안전성)

- 기본 동작은 항상 **복사**입니다. Google Drive 원본이나 네이버 클라우드 인박스 폴더의 파일은
  절대 수정·삭제하지 않습니다. Drive 접근 권한도 읽기 전용(`drive.readonly`)만 요청합니다.
- `--dry-run`은 실제로 계획을 미리 보여주지만, Drive 소스는 정확한 날짜 판별(EXIF 등)을 위해
  파일을 실제로 내려받아 해시/EXIF를 확인합니다. 다만 `library/`, `_review/`, manifest에는
  아무 것도 쓰지 않으므로 실제 실행 전에는 사용자의 디스크 상태나 이후 실행 결과에 영향을 주지
  않습니다.
- 재실행해도 안전합니다(멱등성) — 이미 정리된 사진(sha256 기준)은 다시 복사하지 않고, Drive는
  이미 내려받은 파일을 다시 다운로드하지 않습니다.

## 날짜 판별 우선순위

1. EXIF (`DateTimeOriginal` → `DateTimeDigitized` → `DateTime`, HEIC 포함)
2. 파일명 규칙 (Galaxy, 카카오톡, 안드로이드/iOS 스크린샷, WhatsApp 등 — `config.yaml`의
   `custom_filename_patterns`로 확장 가능)
3. Google Drive 파일 메타데이터 (Drive 출처 파일만)
4. 파일시스템 수정시각 (최후의 수단)
5. 모두 실패 → `_review/`로 이동, 자동 정리하지 않음

`config.yaml`의 `min_confidence_for_auto_organize`보다 낮은 신뢰도는 절대 자동으로 날짜
폴더에 들어가지 않습니다.

## 테스트

```bash
pip install -r requirements-dev.txt
pytest
```

네트워크나 실제 Google 계정 없이 돌아가는 순수 로직 테스트입니다. Drive 연동 자체는
`README.md`의 설정을 마친 뒤 실제 계정으로 수동 확인이 필요합니다.
