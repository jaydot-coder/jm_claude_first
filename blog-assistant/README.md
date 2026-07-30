# blog-assistant

네이버 블로그 초안에 사진을 제자리에 배치해주는 도구입니다. 초안 마크다운과 사진 폴더를 넣으면
**사진이 박힌 단일 HTML 미리보기**와 **삽입 순서대로 번호가 붙은 JPEG 폴더**를 만들어 줍니다.

서버도, API 키도 필요 없습니다. 글을 짓는 일은 PC의 Claude Code가 하고(추가 비용 없음), 이 도구는
렌더링만 담당합니다.

## 전체 흐름

```
[1] 모바일: 사진을 Google Drive 폴더에 업로드
[2] PC: photo-organizer로 사진 내려받기 + 촬영시각순 정리   ← ../photo-organizer
[3] PC: Claude Code로 초안 작성 (메모 + 사진을 같이 보고)
        → [이미지: 파일명 | 설명] 형태로 어떤 사진을 어디에 넣을지 지정
[4] 이 도구: 초안 + 사진 → 미리보기 HTML + 번호 붙은 JPEG
[5] [서식 복사] → 네이버 에디터 붙여넣기 → 사진 순서대로 삽입
```

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 사용법

```bash
python render_post.py <초안.md> --photos <사진폴더> [--out-dir <출력폴더>]
```

예시:

```bash
python render_post.py output/스페인여행_12일차.md \
    --photos ~/naver-blog-photos/library/2025/2025-05-12
```

만들어지는 것:

| 결과물 | 내용 |
|---|---|
| `스페인여행_12일차_preview.html` | 사진이 제자리에 박힌 미리보기. 외부 리소스 없는 단일 파일 |
| `스페인여행_12일차_images/01_….jpg, 02_….jpg …` | 삽입 순서대로 번호가 붙은 JPEG |

터미널에는 사진을 못 찾은 자리와 글에 안 쓰인 사진이 함께 출력됩니다.

### 모바일에서 발행하기

미리보기 HTML은 이미지를 파일 안에 품고 있어서 어디든 올려두면 그대로 열립니다.
미리보기 HTML과 `_images/` 폴더를 같이 Google Drive에 올리면, 모바일에서 HTML을 열어
[서식 복사] → 네이버 블로그 앱에 붙여넣고, 사진은 드라이브 앱에서 번호 순서대로 넣으면 됩니다.

## 초안에 사진을 지정하는 방법

```
[이미지: IMG_2001.jpg | 포르투 캄파냐 기차역 플랫폼]
```

- `파일명`은 사진 폴더에 있는 실제 파일명 (경로 없이 이름만, 대소문자·확장자 생략 허용)
- `설명`은 네이버 이미지탭 노출에 쓰이므로 검색 키워드를 넣는 것이 좋습니다

파일명을 생략하면 촬영시각 순서대로 자동 배치됩니다:

```
[이미지: 리스본 숙소 내부]
```

전체 규칙은 `prompts/naver-blog-format.md`에 있습니다.

## 안전장치

- 사진 폴더의 원본은 읽기만 하고 수정·삭제하지 않습니다
- 초안에 적힌 파일이 폴더에 없으면 **다른 사진으로 대체하지 않고** 경고로 표시합니다
- 같은 사진을 두 번 쓰면 두 번째를 경고로 표시합니다
- 사진을 못 찾은 자리는 `[사진 없음]`으로 표시해 번호가 있는 사진과 구분됩니다
- iPhone HEIC은 네이버 에디터에서 잘 안 받으므로 내보낼 때 JPEG로 변환하고, 촬영 방향(EXIF
  orientation)도 바로잡아 저장합니다

## 프롬프트 자산 (`prompts/`)

Claude Code로 초안을 쓸 때 참조하는 규칙 문서입니다.

| 파일 | 내용 |
|---|---|
| `naver-blog-format.md` | 네이버 포맷·SEO·모바일 줄바꿈 규칙, 이미지 표기 형식 |
| `seo-strategy.md` | 스마트블록 제목 공식, 상위노출 전략 |
| `voice-rules.md` | AI 말투 금지 패턴, 말투 특징 |
| `blog-writer-agent.md` | blog-writer 에이전트 워크플로우 (말투 로드 → 초안 → `output/*.md`) |

말투 샘플(개인 글)은 리포에 커밋하지 않습니다 — `voice-samples.md`로 로컬에 두면 gitignore됩니다.

## 테스트

```bash
pip install -r requirements-dev.txt
pytest
```

사진·네트워크 없이 도는 순수 로직 테스트입니다.
