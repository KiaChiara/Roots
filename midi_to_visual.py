"""
midi_to_visual.py — from a MIDI file, generates the two files for the visualization:
  1) <name>_score.json : the score (time, pitch, amplitude, duration of every note)
  2) <name>_audio.wav  : synthesized working audio

Drums (is_drum tracks) are always excluded: they have no tuned pitch.
All other notes are kept exactly as they are in the MIDI, note by note
(no merging, no changes).

USAGE:
    python3 midi_to_visual.py  input.mid
    python3 midi_to_visual.py  input.mid  --outdir output_folder

Dependencies:  pip install pretty_midi numpy soundfile
ffmpeg is needed (optional) to also get a lighter MP3.

Note: the audio produced is a working synthesis (simple waves), useful for
testing sync. For the final video use the real audio export from your
DAW/Sibelius, aligned to the same starting point as the MIDI.
"""

import argparse
import json
import os
import sys

import numpy as np

try:
    import pretty_midi
    import soundfile as sf
except ImportError:
    sys.exit("A dependency is missing. Install with:\n"
             "  pip install pretty_midi numpy soundfile")

SR = 22050


def extract_notes(inst):
    """All the instrument's notes, note by note, unchanged."""
    out = []
    for n in sorted(inst.notes, key=lambda n: n.start):
        out.append({
            "time": round(float(n.start), 4),
            "freq": round(float(pretty_midi.note_number_to_hz(n.pitch)), 2),
            "amplitude": round(n.velocity / 127.0, 4),
            "duration": round(float(n.end - n.start), 4),
        })
    return out


def synth_events(events, total_len):
    """Additive synthesis with a soft limiter: designed to handle dense mixes too
    (dozens of simultaneous notes) without clipping or squashing everything
    against the peaks."""
    mix = np.zeros(total_len)
    for ev in events:
        freq = ev["freq"]
        dur = ev["duration"]
        n = int(dur * SR)
        if n <= 0:
            continue
        t = np.arange(n) / SR
        # soft wave: fundamental + a little 2nd harmonic (no harshness building up)
        wave = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(2 * np.pi * 2 * freq * t)
        # envelope: short attack, long smooth release (notes blend into each other)
        atk = min(int(0.015 * SR), n // 2)
        rel = min(int(0.25 * SR), n - atk)
        env = np.ones(n)
        if atk > 0:
            env[:atk] = np.linspace(0, 1, atk)
        if rel > 0:
            env[-rel:] = np.cos(np.linspace(0, np.pi / 2, rel))
        i0 = int(ev["time"] * SR)
        # reduced level per voice, so the sum of many notes does not blow up
        seg = wave * env * ev["amplitude"] * 0.25
        mix[i0:i0 + len(seg)] += seg

    # soft limiter (tanh): gently compresses peaks instead of clipping them,
    # so a few dense moments do not squash the level of everything else.
    mix = np.tanh(mix * 0.6) / 0.6
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.9
    return mix

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input MIDI file (.mid)")
    ap.add_argument("--outdir", default=".", help="output folder (default: current)")
    args = ap.parse_args()

    pm = pretty_midi.PrettyMIDI(args.input)
    base = os.path.splitext(os.path.basename(args.input))[0]
    os.makedirs(args.outdir, exist_ok=True)

    all_events = []
    print("Instruments:")
    for inst in pm.instruments:
        if inst.is_drum:
            print(f"  - {inst.name or 'unnamed'}: EXCLUDED (drums)")
            continue
        if not inst.notes:
            continue
        ev = extract_notes(inst)
        all_events.extend(ev)
        print(f"  - {inst.name or 'unnamed'}: {len(ev)} notes")

    if not all_events:
        sys.exit("No pitched notes found in the MIDI file.")

    events = sorted(all_events, key=lambda e: e["time"])
    duration = float(pm.get_end_time())

    score = {
        "source_file": os.path.basename(args.input),
        "duration": round(duration, 4),
        "num_events": len(events),
        "events": events,
    }
    score_path = os.path.join(args.outdir, base + "_score.json")
    with open(score_path, "w") as f:
        json.dump(score, f, indent=2)
    print(f"\nScore:  {score_path}  ({len(events)} events)")

    total_len = int((duration + 1) * SR)
    mix = synth_events(events, total_len)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.85
    wav_path = os.path.join(args.outdir, base + "_audio.wav")
    sf.write(wav_path, mix.astype("float32"), SR)
    print(f"Audio:  {wav_path}  ({round(len(mix)/SR,1)}s)")

    mp3_path = os.path.join(args.outdir, base + "_audio.mp3")
    if os.system(f'ffmpeg -y -loglevel error -i "{wav_path}" -codec:a libmp3lame -qscale:a 4 "{mp3_path}"') == 0:
        print(f"Audio:  {mp3_path}  (lighter mp3)")

    print("\nDone. Load the _score.json and the _audio into the visualizer.")
    print("Note: the audio is a working synthesis; for the final video use the real export from your DAW.")


if __name__ == "__main__":
    main()
