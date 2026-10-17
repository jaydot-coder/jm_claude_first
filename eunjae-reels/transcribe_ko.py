import sys, wave, numpy as np, sherpa_onnx
D = sys.argv[1]; W = sys.argv[2]
rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=f"{D}/encoder-epoch-99-avg-1.onnx", decoder=f"{D}/decoder-epoch-99-avg-1.onnx",
    joiner=f"{D}/joiner-epoch-99-avg-1.onnx", tokens=f"{D}/tokens.txt", num_threads=2, sample_rate=16000, feature_dim=80)
w = wave.open(W); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
def run(a, b, gain=1.0):
    seg = x[int(max(0, a) * sr):int(min(len(x) / sr, b) * sr)] * gain
    seg = np.clip(seg, -1, 1)
    s = rec.create_stream(); s.accept_waveform(sr, seg); rec.decode_stream(s); return s.result.text.strip()
print("WHOLE:", run(0, 30), "|| x3:", run(0, 30, 3.0))
segs = [(0.2,1.0),(1.8,2.7),(3.5,4.5),(5.3,6.0),(6.7,8.9),(9.9,10.5),(11.2,11.7),(13.0,13.7),(14.8,15.2),(16.7,17.4),(18.7,19.1),(20.6,21.6),(22.8,23.5)]
for i, (a, b) in enumerate(segs, 1):
    print(f"S{i:<2} {a:5.1f}-{b:5.1f}  p0.3:{run(a-.3,b+.3)!r:14} p0.3x3:{run(a-.3,b+.3,3.0)!r:14} p0.8x3:{run(a-.8,b+.8,3.0)!r}")
