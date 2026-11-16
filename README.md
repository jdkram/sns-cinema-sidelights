---
human-contributors: ["Jonny Kram"]
---

# Star and Shadow sidelight controller

Twenty-four dimmable LED panels beside the cinema screen, driven by a Raspberry Pi Zero W above the screen and five buttons in the projection booth.

## Status (November 2026)

The lights work, with faults: panels look completely off below roughly 27% brightness, and a single panel lit on its own has never been seen to light. The cause is not known yet. The Pi still runs the original 2018 C++ program on an operating system from 2017.

This repository now holds the replacement: a Python controller that has been tested on a laptop but **has not yet run on the real lights**. [PLAN.md](PLAN.md) is the one path from here to working, programmable lights. Start there.

## What is where

| Path | What it is |
|---|---|
| [PLAN.md](PLAN.md) | The steps, in order, with what is done and what is blocked |
| [HARDWARE.md](HARDWARE.md) | What is known about the physical system, and how well each fact is supported |
| [SETUP.md](SETUP.md) | Building the Pi's SD card, network access, day-to-day commands |
| `probe.py` | Standalone hardware tester. Runs on any Pi with no setup |
| `sidelights/` | The controller: sequence engine, patterns, terminal preview, hardware output |
| `sessions/` | Checklists and notes from visits to the cinema |
| `config/systemd/` | The service file that starts the controller at boot |

Hardware photos, older notes and the projectionists' quick guide live on the Star and Shadow Nextcloud (volunteer account needed).

## Preview a pattern on a laptop

Needs Python 3.10 or newer and a Linux, macOS or WSL terminal. No packages.

```bash
python3 -m sidelights.preview --list
```

```bash
python3 -m sidelights.preview ember
```

## Write a new pattern

1. Add a class to `sidelights/sequences.py`. Copy a short one such as `SequenceBreathing` to start from. The constructor schedules events; all times are in seconds and brightness is 0-100.
2. Add it to the `SEQUENCES` dictionary at the bottom of that file.
3. Preview it until it looks right.
4. To put it on a booth button, change `BUTTON_SEQUENCES` in `sidelights/config.py`.
5. On the Pi: `git pull`, then `sudo systemctl restart sns-sidelights.service`.

There are three kinds of event, each with an `_all_leds` variant:

| Call | Effect |
|---|---|
| `fade_event_add(led, brightness, start, length)` | Smooth fade from wherever the LED is now to `brightness` |
| `brightness_set_event_add(led, brightness, time_s)` | Instant jump at `time_s` |
| `pulse_event_add(led, brightness, time_s, length)` | Jump on, hold for `length`, jump to off |

For a looping pattern pass `loop=True` and set `self._length_seconds`.

## Buttons

| Button | Sequence |
|---|---|
| 1 | `ambient`: slow random fades |
| 2 | `fadeout`: everything fades to off |
| 3 | `heartbeat`: double pulse |
| 4 | `static75`: steady house lights |
| 5 | `ambienthigh`: ambient that never drops below 30% |

The source of truth is `BUTTON_SEQUENCES` in `sidelights/config.py`.

## If the lights misbehave during a screening

1. Press button 2. Everything fades to off within ten seconds.
2. If that does nothing, switch off the two power strips above the screen (long stick from the bar, short stepladder). This cuts power to the controller as well.

With remote access, the equivalent is in [SETUP.md](SETUP.md#day-to-day-commands).

## Rules for this repository

- No passwords, keys, Wi-Fi names or IP addresses. Share those directly between maintainers.
- A statement about the hardware goes in [HARDWARE.md](HARDWARE.md) with how it is known. If it has not been observed, it is listed as unknown.
- The 2018 C++ controller is in git history (last at commit `630d49a`).
