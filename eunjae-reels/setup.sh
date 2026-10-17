#!/bin/bash
# 은재왔지 릴스 환경 설치. 클라우드 환경의 Setup script 칸에 이 내용을 그대로 붙여 넣는다.
# 저장소 파일에 의존하지 않음(Setup script는 저장소 복제 전에 돌 수 있음). 우분투 24.04, root.
# 약 5분 안에 끝나야 환경 캐시가 만들어짐 -> 모델 2개는 병렬 다운로드(합계 약 1.4GB).
# 실패해도 세션이 막히지 않도록 항상 0으로 끝냄(필요한 것이 없으면 작업 때 다시 시도).
M=/opt/eunjae-asr
R=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
mkdir -p "$M"
dl() { [ -d "$M/$1" ] || curl -fsSL --retry 3 "$R/$1.tar.bz2" | tar -xj -C "$M"; }
dl sherpa-onnx-whisper-large-v3 &              # 음성 인식 1: Whisper large-v3 (약 1.07GB)
dl sherpa-onnx-zipformer-korean-2024-06-24 &   # 음성 인식 2: 한국어 전용 (약 330MB), 교차 확인용
python3 -m pip install -q --break-system-packages sherpa-onnx numpy scipy pillow &
command -v ffmpeg >/dev/null || { apt-get update -q && apt-get install -y -q ffmpeg; } &
wait
exit 0
