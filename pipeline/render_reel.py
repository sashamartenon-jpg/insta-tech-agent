#!/usr/bin/env python3
"""Render a faceless reel from post.json beats: 1080x1920 H.264 + AAC, burned captions.

Per beat: synthesize the voice line, draw a frame (big on-screen text + caption
of what is being said), slow-zoom it for the length of the audio, then concat.

TTS order: Piper (neural, offline) -> espeak-ng -> silence (timed at 165 wpm).
The engine actually used is written to render.json so the PR can flag fallbacks.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from common import BRAND, CONFIG, ROOT, draw_rich, fit_rich, font, hex_rgb, load_post, new_canvas

W, H, FPS = 1080, 1920, 30
M = 90
FG = hex_rgb(BRAND["fg"])
ACC = hex_rgb(BRAND["accent"])
MUTED = hex_rgb(BRAND["muted"])
PANEL = hex_rgb(BRAND["panel"])
CODE_BG = hex_rgb(BRAND["code_bg"])
VOICES = Path(os.environ.get("PIPER_VOICES", ROOT / ".voices"))


# ------------------------------------------------------------------ TTS
_piper = None


def tts_piper(text, wav_path):
    global _piper
    from piper import PiperVoice  # noqa: import inside: optional dependency
    if _piper is None:
        model = VOICES / f"{CONFIG['tts']['voice']}.onnx"
        if not model.exists():
            raise FileNotFoundError(model)
        _piper = PiperVoice.load(str(model))
    with wave.open(str(wav_path), "wb") as wf:
        try:  # piper-tts >= 1.3
            from piper import SynthesisConfig
            cfg = SynthesisConfig(length_scale=CONFIG["tts"].get("length_scale", 1.0))
            _piper.synthesize_wav(text, wf, syn_config=cfg)
        except ImportError:  # older API
            _piper.synthesize(text, wf, length_scale=CONFIG["tts"].get("length_scale", 1.0))


def tts_espeak(text, wav_path):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise FileNotFoundError("espeak-ng")
    subprocess.run([exe, "-v", "fr-fr", "-s", "170", "-w", str(wav_path), text], check=True,
                   capture_output=True)


def tts_silence(text, wav_path):
    secs = max(1.2, len(text.split()) / 2.75)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", f"{secs:.2f}", str(wav_path)], check=True)


def synthesize(text, wav_path):
    for name, fn in (("piper", tts_piper), ("espeak", tts_espeak), ("silence", tts_silence)):
        try:
            fn(text, wav_path)
            return name
        except Exception as e:  # fall through to the next engine
            last = e
    raise RuntimeError(f"all TTS engines failed: {last}")


def duration(wav_path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(wav_path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


# ------------------------------------------------------------------ frames
def caption_box(d, text):
    """What is being said, bottom third, readable with sound off."""
    f, lines, h = fit_rich(d, text, "semibold", W - 2 * M - 60, 330, 50, 36, 1.22)
    top = H - 560
    d.rounded_rectangle([M, top, W - M, top + h + 60], radius=28, fill=PANEL)
    draw_rich(d, lines, f, M + 30, top + 30, FG, ACC, align="center", box_width=W - 2 * M - 60,
              line_gap=1.22)


def frame(beat, idx, total, handle):
    img, d = new_canvas(W, H)
    kind = beat.get("kind", "text")
    screen = beat.get("screen", "")
    zone_top, zone_h = 300, 900
    if kind == "code":
        lines = screen.split("\n")
        size = 52
        while size > 26:
            f = font("mono", size)
            if max(d.textlength(l, font=f) for l in lines) <= W - 2 * M - 80:
                break
            size -= 2
        f = font("mono", size)
        box_h = len(lines) * size * 1.5 + 130
        y = zone_top + (zone_h - box_h) / 2
        d.rounded_rectangle([M, y, W - M, y + box_h], radius=30, fill=CODE_BG, outline=(40, 46, 60), width=2)
        for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([M + 34 + i * 36, y + 32, M + 56 + i * 36, y + 54], fill=col)
        cy = y + 90
        for line in lines:
            d.text((M + 44, cy), line, font=f, fill=ACC if line.startswith("$ ") else (220, 226, 236))
            cy += size * 1.5
    elif kind == "stat":
        vf, vl, vh = fit_rich(d, screen, "bold", W - 2 * M, 420, 280, 100, 1.0)
        lf, ll, lh = fit_rich(d, beat.get("label", ""), "semibold", W - 2 * M, 240, 64, 40, 1.15)
        y = zone_top + (zone_h - vh - lh - 30) / 2
        draw_rich(d, vl, vf, M, y, ACC, ACC, align="center", box_width=W - 2 * M, line_gap=1.0)
        draw_rich(d, ll, lf, M, y + vh + 30, FG, ACC, align="center", box_width=W - 2 * M, line_gap=1.15)
    else:
        start = 128 if kind == "title" else 104
        fnt, lines, h = fit_rich(d, screen, "bold", W - 2 * M, zone_h, start, 56, 1.06)
        y = zone_top + (zone_h - h) / 2
        draw_rich(d, lines, fnt, M, y, FG, ACC, align="center", box_width=W - 2 * M, line_gap=1.06)
    caption_box(d, beat["voice"])
    # progress bar + handle
    d.rectangle([0, 0, W * idx / total, 10], fill=ACC)
    hf = font("semibold", 34)
    d.text(((W - d.textlength(handle, font=hf)) / 2, H - 170), handle, font=hf, fill=MUTED)
    return img


def render(post_dir):
    post_dir = Path(post_dir)
    post = load_post(post_dir)
    beats = post["reel"]["beats"]
    handle = CONFIG["account"]["handle"]
    engines, clips = [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, beat in enumerate(beats, 1):
            png, wav, clip = tmp / f"{i:02d}.png", tmp / f"{i:02d}.wav", tmp / f"{i:02d}.mp4"
            frame(beat, i, len(beats), handle).save(png)
            if i == 1:
                frame(beat, i, len(beats), handle).convert("RGB").save(post_dir / "cover.jpg", "JPEG", quality=92)
            engines.append(synthesize(beat["voice"], wav))
            dur = duration(wav) + 0.30
            frames = int(dur * FPS) + 1
            zoom = f"zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-i", str(wav),
                "-filter_complex", f"[0:v]scale={int(W*1.5)}:-1,{zoom},format=yuv420p[v];[1:a]apad,aresample=48000[a]",
                "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
                "-c:a", "aac", "-b:a", "160k", "-ac", "2", str(clip)], check=True)
            clips.append(clip)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{c}'\n" for c in clips))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                        "-movflags", "+faststart", str(post_dir / "reel.mp4")], check=True)
    total = duration(post_dir / "reel.mp4")
    meta = {"engine": sorted(set(engines)), "seconds": round(total, 1), "beats": len(beats)}
    (post_dir / "render.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("post_dir")
    print(json.dumps(render(ap.parse_args().post_dir)))
