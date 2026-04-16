import os, time
import soundfile as sf
import soxr

def now():
    return time.strftime("%H:%M:%S")

t0 = time.time()
print(f"[{now()}] === VocalSet 24kHz リサンプリング ===", flush=True)

base = "/root/data/VocalSet11/FULL"
target_sr = 24000
singers = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and (d.startswith("female") or d.startswith("male"))])

total = 0
errors = 0
for singer in singers:
    singer_path = os.path.join(base, singer)
    wav24k_dir = os.path.join(singer_path, "wav_24k")
    wav_dir = os.path.join(singer_path, "wav")
    os.makedirs(wav24k_dir, exist_ok=True)
    os.makedirs(wav_dir, exist_ok=True)
    count = 0
    for root, dirs, files in os.walk(singer_path):
        if "/straight/" in root + "/" or "/vibrato/" in root + "/":
            for f in files:
                if f.endswith(".wav"):
                    src = os.path.join(root, f)
                    dst_24k = os.path.join(wav24k_dir, f)
                    dst_link = os.path.join(wav_dir, f)
                    if not os.path.exists(dst_24k):
                        try:
                            data, sr = sf.read(src)
                            if sr != target_sr:
                                data = soxr.resample(data, sr, target_sr)
                            sf.write(dst_24k, data, target_sr, subtype="PCM_16")
                        except Exception as e:
                            print(f"ERROR: {f}: {e}")
                            errors += 1
                            continue
                    if not os.path.exists(dst_link):
                        os.symlink(dst_24k, dst_link)
                    count += 1
    total += count
dt = time.time() - t0
print(f"[{now()}] VocalSet完了: {total} files, {errors} errors ({dt:.1f}s)", flush=True)

t0 = time.time()
print(f"[{now()}] === LibriTTS-R wav/ symlinks ===", flush=True)
subsets = ["train-clean-100", "train-clean-360", "dev-clean", "test-clean"]
libritts_total = 0
for subset in subsets:
    subset_dir = f"/root/data/LibriTTS_R/{subset}"
    count = 0
    for speaker in os.listdir(subset_dir):
        speaker_path = os.path.join(subset_dir, speaker)
        if not os.path.isdir(speaker_path):
            continue
        wav_dir = os.path.join(speaker_path, "wav")
        os.makedirs(wav_dir, exist_ok=True)
        for chapter in os.listdir(speaker_path):
            chapter_path = os.path.join(speaker_path, chapter)
            if not os.path.isdir(chapter_path) or chapter in ("wav", "hdf5"):
                continue
            for f in os.listdir(chapter_path):
                if f.endswith(".wav"):
                    src = os.path.join(chapter_path, f)
                    dst = os.path.join(wav_dir, f)
                    if not os.path.exists(dst):
                        os.symlink(src, dst)
                        count += 1
    print(f"  {subset}: {count} symlinks", flush=True)
    libritts_total += count
dt = time.time() - t0
print(f"[{now()}] LibriTTS-R完了: {libritts_total} symlinks ({dt:.1f}s)", flush=True)
