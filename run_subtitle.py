"""Quick runner: transcribe + burn subtitles on a video."""
import subprocess, os, stable_whisper, sys
sys.path.insert(0, os.path.dirname(__file__))
from services.subtitler import _burn_subtitles

SOURCE = "/Users/levavdosin/Desktop/hf_20260317_170409_0aa7beca-e364-4952-8404-937d0492a7cb (1).mp4"
OUTPUT = "/Users/levavdosin/Desktop/hf_20260317_170409_0aa7beca-e364-4952-8404-937d0492a7cb_subtitled.mp4"
AUDIO = "/tmp/sub_audio.wav"

print("Extracting audio...")
subprocess.run(["ffmpeg","-y","-i",SOURCE,"-vn","-acodec","pcm_s16le","-ar","16000","-ac","1",AUDIO], check=True, capture_output=True)

print("Transcribing...")
model = stable_whisper.load_model("base")
result = model.transcribe(AUDIO)
words = []
for seg in result.segments:
    for w in seg.words:
        words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
os.remove(AUDIO)

print(f"Found {len(words)} words:")
for w in words:
    print(f"  [{w['start']:.2f}-{w['end']:.2f}] {w['word']}")

print("\nBurning subtitles...")
_burn_subtitles(SOURCE, words, OUTPUT)
print(f"\n✓ Done: {OUTPUT}")
