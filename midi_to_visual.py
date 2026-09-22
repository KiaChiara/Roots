"""
midi_to_visual.py — da un file MIDI genera i due file per la visualizzazione:
  1) <nome>_score.json : la partitura (tempo, altezza, ampiezza, durata di ogni nota)
  2) <nome>_audio.wav  : audio di lavoro sintetizzato

La batteria (tracce is_drum) viene sempre esclusa: non ha altezza intonata.
Tutte le altre note vengono riportate cosi' come sono nel MIDI, nota per nota
(nessuna fusione, nessuna modifica).

USO:
    python3 midi_to_visual.py  input.mid
    python3 midi_to_visual.py  input.mid  --outdir cartella_output

Dipendenze:  pip install pretty_midi numpy soundfile
Per ottenere anche un MP3 piu' leggero serve ffmpeg (opzionale).

NB: l'audio prodotto e' una sintesi di lavoro (onde semplici), utile per testare
la sincronia. Per il video finale usa l'export audio reale dal tuo DAW/Sibelius,
allineato allo stesso punto di partenza del MIDI.
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
    sys.exit("Manca una dipendenza. Installa con:\n"
             "  pip install pretty_midi numpy soundfile")

SR = 22050


def extract_notes(inst):
    """Tutte le note dello strumento, nota per nota, senza modifiche."""
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
    """Sintesi additiva con soft-limiter: pensata per reggere anche mix densi
    (decine di note simultanee) senza saturare ne' schiacciare tutto sui picchi."""
    mix = np.zeros(total_len)
    for ev in events:
        freq = ev["freq"]
        dur = ev["duration"]
        n = int(dur * SR)
        if n <= 0:
            continue
        t = np.arange(n) / SR
        # onda morbida: fondamentale + poca 2a armonica (niente asprezza che si accumula)
        wave = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(2 * np.pi * 2 * freq * t)
        # inviluppo: attacco breve, release lungo e morbido (le note si legano)
        atk = min(int(0.015 * SR), n // 2)
        rel = min(int(0.25 * SR), n - atk)
        env = np.ones(n)
        if atk > 0:
            env[:atk] = np.linspace(0, 1, atk)
        if rel > 0:
            env[-rel:] = np.cos(np.linspace(0, np.pi / 2, rel))
        i0 = int(ev["time"] * SR)
        # volume ridotto per voce, cosi' la somma di molte note non esplode
        seg = wave * env * ev["amplitude"] * 0.25
        mix[i0:i0 + len(seg)] += seg

    # soft-limiter (tanh): comprime dolcemente i picchi invece di tagliarli;
    # evita che pochi istanti densi schiaccino il volume di tutto il resto.
    mix = np.tanh(mix * 0.6) / 0.6
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.9
    return mix

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="file MIDI (.mid) in ingresso")
    ap.add_argument("--outdir", default=".", help="cartella di output (default: corrente)")
    args = ap.parse_args()

    pm = pretty_midi.PrettyMIDI(args.input)
    base = os.path.splitext(os.path.basename(args.input))[0]
    os.makedirs(args.outdir, exist_ok=True)

    all_events = []
    print("Strumenti:")
    for inst in pm.instruments:
        if inst.is_drum:
            print(f"  - {inst.name or 'senza nome'}: ESCLUSO (batteria)")
            continue
        if not inst.notes:
            continue
        ev = extract_notes(inst)
        all_events.extend(ev)
        print(f"  - {inst.name or 'senza nome'}: {len(ev)} note")

    if not all_events:
        sys.exit("Nessuna nota melodica trovata nel MIDI.")

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
    print(f"\nScore:  {score_path}  ({len(events)} eventi)")

    total_len = int((duration + 1) * SR)
    mix = synth_events(events, total_len)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.85
    wav_path = os.path.join(args.outdir, base + "_audio.wav")
    sf.write(wav_path, mix.astype("float32"), SR)
    print(f"Audio:  {wav_path}  ({round(len(mix)/SR,1)}s)")

    mp3_path = os.path.join(args.outdir, base + "_audio.mp3")
    if os.system(f'ffmpeg -y -loglevel error -i "{wav_path}" -codec:a libmp3lame -qscale:a 4 "{mp3_path}"') == 0:
        print(f"Audio:  {mp3_path}  (mp3 piu' leggero)")

    print("\nFatto. Carica lo _score.json e l'_audio nel visualizzatore.")
    print("NB: l'audio e' una sintesi di lavoro; per il video finale usa l'export reale dal tuo DAW.")


if __name__ == "__main__":
    main()
