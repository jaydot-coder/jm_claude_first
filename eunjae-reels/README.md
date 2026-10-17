# eunjae-reels — 은재왔지 릴스 제작 도구

핸드폰으로 찍은 영상에 제목과 음성 자막을 얹어 인스타 릴스(1080x1920)로 만드는 스크립트 모음.
채팅 세션에서 만든 것을 코드 모드로 옮긴 것. 작업 요령과 주의점은 `.claude/skills/eunjae-reels/SKILL.md` 참고.

## 설치
- `setup.sh` 내용을 클라우드 환경의 **Setup script** 칸에 붙여 넣는다(한 번만).
- 모델은 `/opt/eunjae-asr/` 에 설치됨. 로컬 PC에서 쓸 때는 `bash setup.sh` 후 경로만 맞추면 됨.

## 파일
| 파일 | 용도 |
|---|---|
| `make_reel2.py` | 제목(색 구분) + 인스타 세이프존 음성 자막. HDR(HLG) 원본의 색을 그대로 유지. **음성 자막 릴스는 이것** |
| `make_reel.py` | 소리 세기에 맞춰 움직이는 의성어 자막 + 큰 훅 제목(새벽소리 릴스용) |
| `make_hf_index.py` | 위 의성어 릴스를 HyperFrames(HTML+GSAP)로 만드는 선택 경로 |
| `transcribe.py`, `transcribe_ko.py` | 음성 인식 두 모델(Whisper large-v3, 한국어 zipformer) 교차 확인용 |
| `fonts/Jua-Regular.ttf` | 기본 자막 글씨체 Jua (SIL OFL, Google Fonts) |

## 사용 예
```bash
# 음성 인식 (자막 후보 뽑기)
ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 audio.wav
python3 -I transcribe.py    /opt/eunjae-asr/sherpa-onnx-whisper-large-v3 audio.wav
python3 -I transcribe_ko.py /opt/eunjae-asr/sherpa-onnx-zipformer-korean-2024-06-24 audio.wav

# 제목 + 음성 자막 릴스 (make_reel2.py 안의 SEGS/제목 글자를 먼저 고칠 것)
python3 -I make_reel2.py in.mp4 fonts/Jua-Regular.ttf out.mp4
# 세이프존 확인용 한 컷: ... fonts/Jua-Regular.ttf out.mp4 7.5 guide.png
```
`make_reel2.py`의 `DUR`(영상 길이)과 `SEGS`(말 시작·끝·글자), 제목 글자, `transcribe.py`의 `segs`는 영상마다 바꿔야 하는 값이다.
