from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import glob, os
tfevents = sorted(glob.glob("/workspace/exp/sifigan_1000k/events.out.tfevents.*"), key=os.path.getsize, reverse=True)
ea = EventAccumulator(tfevents[0], size_guidance={"scalars": 0})
ea.Reload()

keys = ["train/mel_loss", "train/adv_loss", "train/fm_loss", "train/reg_loss", "train/discriminator_loss",
        "eval/mel_loss", "eval/generator_loss", "eval/discriminator_loss"]
milestones = [300000, 400000, 500000, 600000, 700000, 800000, 900000]
header = "key".ljust(30)
for s in milestones:
    header += f"{s:>9d}"
print(header)
print("-" * len(header))
for k in keys:
    events = ea.Scalars(k)
    step_to_val = {e.step: e.value for e in events}
    row = k.ljust(30)
    for s in milestones:
        nearest = min(step_to_val.keys(), key=lambda x: abs(x-s))
        row += f"{step_to_val[nearest]:9.4f}"
    print(row)

print("\n=== 800k以降の傾向 (最初10点 vs 最新10点) ===")
for k in ["train/mel_loss", "eval/mel_loss", "train/adv_loss", "train/discriminator_loss", "train/reg_loss", "train/fm_loss"]:
    events = ea.Scalars(k)
    recent = [e for e in events if e.step >= 800000]
    if len(recent) < 10: continue
    first10 = sum(e.value for e in recent[:10])/10
    last10 = sum(e.value for e in recent[-10:])/10
    delta = last10 - first10
    arrow = "DOWN" if delta < 0 else "UP" if delta > 0.001 else "FLAT"
    print(f"  {k:<30} {first10:.4f} -> {last10:.4f}  delta={delta:+.4f} [{arrow}]")

print("\n=== 最新値 ===")
for k in keys:
    events = ea.Scalars(k)
    last = events[-1]
    print(f"  step {last.step:>7d}  {k:<30} {last.value:.4f}")
