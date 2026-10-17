import sys, wave, numpy as np, sherpa_onnx
M = sys.argv[1]; W = sys.argv[2]
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{M}/large-v3-encoder.int8.onnx", decoder=f"{M}/large-v3-decoder.int8.onnx",
    tokens=f"{M}/large-v3-tokens.txt", language="ko", task="transcribe", num_threads=2)
w = wave.open(W); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
def run(a, b):
    s = rec.create_stream(); s.accept_waveform(sr, x[int(max(0, a) * sr):int(min(len(x) / sr, b) * sr)]); rec.decode_stream(s); return s.result.text.strip()
print("WHOLE:", run(0, 30))
segs = [(0.2,1.0),(1.8,2.7),(3.5,4.5),(5.3,6.0),(6.7,8.9),(9.9,10.5),(11.2,11.7),(13.0,13.7),(14.8,15.2),(16.7,17.4),(18.7,19.1),(20.6,21.6),(22.8,23.5)]
for a, b in segs:
    print(f"{a:5.1f}-{b:5.1f}  pad0.3: {run(a-0.3, b+0.3)!r}  |  pad1.0: {run(a-1.0, b+1.0)!r}")
