---
human-contributors: ["Jonny Kram"]
---

# Sessions 001-005 (March 2026): what happened

The full checklists are in git history (last present at commit `630d49a`). This is everything from them worth carrying forward. Facts with their evidence are in [HARDWARE.md](../HARDWARE.md).

## 001 and 003, 13 March: getting the 2018 code to build again

- The Pi turned out to be on Raspbian Stretch with Python 3.5.3. Package sources had to be pointed at `archive.debian.org` before `apt` worked.
- wiringPi was half installed: the library file had to be copied into place by hand, and the build told where its headers were.
- I2C speed was raised from 100 kHz to 400 kHz in `/boot/config.txt`.
- Buttons 1-3 (Ambient, FadeOut, HeartBeat) worked. Sparkle showed only its final full-on. KnightRider and Ember showed nothing, on the old program and the rebuilt one.
- A sleep was added to the main loop on the theory that I2C was saturated. It made no difference.
- A "fix" swapped full-off for full-on at 100% brightness, which turned 100% into off. Reverted.
- Hand-written Python probe scripts showed nothing, because of bugs in the scripts.

## 002: remote access

Planned (SSH keys, cinema Wi-Fi, Tailscale on the Pi), never run. Superseded by [SETUP.md](../SETUP.md).

## 004, 18 March: tests that bypass the sequence engine

- All 24 on: 24 lit. All at 50%: steady. Ramp of all 24: visible from about 27%.
- One panel at a time: "LED 1 dead" was written down and the other 23 rows left blank. A later note says no panel was visible from where the tester stood.
- Buttons 4 and 5 were changed to Static 75% and AmbientHigh so the cinema had five usable buttons.
- The write-up concluded that the sequence engine could not drive single panels. The evidence did not support that: the bypass test showed the same thing.

## 005: planned, never run

Would have tested a single panel through the engine and timed I2C writes.

## What was learned about working on this

- Most of the effort went on theories about software while the open questions were physical. Measure first.
- Record where you stood and whether the house lights were on. "Nothing visible" was ambiguous for months.
- Fill in every row. One "dead" and 23 blanks cost a later session.
