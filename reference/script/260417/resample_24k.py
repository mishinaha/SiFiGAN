import os, soundfile as sf, soxr
in_dir = "/root/anasyn/in"
out_dir = "/root/anasyn/out"
target_sr = 24000
for f in sorted(os.listdir(in_dir)):
    if not f.endswith(".wav"):
        continue
    src = os.path.join(in_dir, f)
    dst = os.path.join(out_dir, f.replace(".wav", "_original_24k.wav"))
    data, sr = sf.read(src)
    if sr != target_sr:
        data = soxr.resample(data, sr, target_sr)
    sf.write(dst, data, target_sr, subtype="PCM_16")
    print(f"{f}: {sr} -> {target_sr}  {data.shape}  -> {os.path.basename(dst)}")
