---
title: Roots (내 고향)
emoji: 🗺️
colorFrom: blue
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
---

# Roots — 내 고향

*A sound map of the place I come from and the place I now call home.*

*내가 떠나온 곳과 지금 사는 곳의 소리 지도.*

**Roots** turns a piece of music into a drawing traced over the silhouette of a place that
matters to me. Each note of a MIDI file becomes a flowing curve, positioned by pitch and
coloured along a blue-to-green gradient. The drawing accumulates as the music plays, clipped
to the shape of the map.

This is a personal work, built around the places I belong to:

- **Seoul and South Korea** — where I live now, traced along the Han River
- **Rome and Italy** — where I come from, divided by the Tevere River

Seoul and Rome are hand-drawn: not generic outlines, but shapes I chose and drew myself,
because this piece is about *my* maps — not any map.

## Two ways to see it

- **View in browser** — a live, interactive visualization you can play, scrub, screenshot,
  and record.
- **Generate MP4** — an offline, full-quality render exported as a video file.

You can use the working audio synthesized from the MIDI, or upload your own audio track
(for example, a real recording of the same piece).

## Running locally

Requires Python 3 and `ffmpeg` (for MP4 export).

```bash
pip install -r requirements.txt
python3 app.py
```

Then open the local URL shown in the terminal (usually `http://127.0.0.1:7860`).

## How it works

1. **MIDI → score.** The file is parsed into notes (time, pitch, amplitude, duration);
   drum tracks are excluded, since they have no pitch.
2. **Audio.** A working audio track is synthesized from the score, or a track you upload is
   used instead.
3. **Visualization.** Each note is drawn as a curved line with distant anchor points and
   Perlin-noise variation, so the strokes fan out organically. Curves accumulate at low
   opacity, with a brief brighter flash on each new note. A mask clips everything to the
   chosen shape. For Italy, the pitch axis is rotated so low notes sit at the bottom and
   high notes at the top, following the vertical form of the country.

## An open extension

This work has an open, participatory companion — **Roots (Open) — 모두의 고향** — where
anyone can pick their own country or city and see it become a sound map:
👉 https://github.com/YOUR-USERNAME/roots-open

## Author

Created by **Chiara Giustiniani**.

## Also included

`midi_to_visual.py` is a small command-line tool that generates the score (JSON) and a
working audio file from a MIDI, without the interface — for anyone who just wants the data.
