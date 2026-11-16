---
human-authors: Jonny Kram
session-date: (next visit)
session-number: "008"
---

# Session 008: find the fault in the controller box

**Status:** plan, written 2026-11-16 evening. Nothing here has been run.
**Read first:** `PSU_FAULT.md` (what we know and why), `HARDWARE.md`.

## Where we are

- The lights work as whole-wall patterns under the Python controller. Booth buttons
  1-5 are verified. Nothing is broken for projectionists.
- The fault: lightboxes can't be lit on their own. All 24 on is fine. 20 to 23 on
  dims every lit box together and hums. 19 or fewer on is dark. It depends on how
  many are on, not which.
- Each lightbox has its own 12 V driver. The controller box only sends dimming
  signals. So the fault is in something shared, most likely inside the controller box.
- **Two theories have already been wrong** (the March "event engine" bug, then the
  "single power supply"). Both were guesses that got written up as fact. This session
  is for measuring. Write down what was seen and who saw it, and keep it separate
  from what it might mean.

Leading idea, untested: every channel's dimming line is pulled up to a common rail on
the stripboard, and that rail sags as more channels are held off. Possible causes: a
wrong or weak power adapter fitted to the box after the 2023 repair, or a supply wire
on the wrong pin.

## Before going in

- [ ] Sync the Pi to the rewritten repo (files differ only in comment lines):
      `ssh sns-sidelights 'cd ~/sidelights && git fetch && git reset --hard origin/main'`
- [ ] Bring: multimeter, phone for photos, the 2023 controller box photo
      (`IMG_20231020_161104.jpg` on Nextcloud) to compare against, a second person.
- [ ] Remote access works from off-site (`ssh sns-sidelights` on Jonny's home
      machine). Someone at home can drive while someone on site watches the wall.

Holding a test state (stop the service first, start it again after):

```bash
ssh sns-sidelights
sudo systemctl stop sns-sidelights-py.service
cd ~/sidelights
python3 probe.py all 100        # all 24 on
python3 -c "import probe as p; L=p.Lights(p.Bus()); L.set_all(100); [L.set(i,0) for i in range(1,2)]; L.show()"   # 23 on (LED 1 off)
python3 -c "import probe as p; L=p.Lights(p.Bus()); L.set_all(100); [L.set(i,0) for i in range(1,6)]; L.show()"   # 19 on
sudo systemctl start sns-sidelights-py.service
```

## Part 1: from the floor (no ladder, no meter)

- [ ] Count the mains plugs on the "LIGHT BOX ONLY" strips, left and right: ____ / ____
      (expect about 24 in total, plus the controller's).
- [ ] With all 24 on, unplug **one** lightbox's mains lead. Exactly one box goes dark? ____
- [ ] Find the controller box's power adapter and read its label: ____ V  ____ A.
      Photograph it. What does the lead plug into on the box? ____
- [ ] **Power-on order** (a 2024 note says the lights may have failed after the
      lightboxes were powered before the controller). Switch everything off at the
      strips. Then:
      - Controller first, wait 2 minutes, then lightboxes. Hold 19 on. Dark or lit? ____
      - Lightboxes first, then controller. Hold 19 on. Dark or lit? ____

## Part 2: one person watching, one driving (no ladder)

- [ ] Is the threshold really just the count? Hold these and note what's seen:
      - LEDs 1-12 on, 13-24 off (one whole board): ____
      - LEDs 13-24 on, 1-12 off: ____
      - Every other LED on (12 on, spread out): ____
- [ ] Does it take time? Go from all 24 on to 23 on and watch: does the wall dim at
      once, or sag over a second or two? ____
- [ ] The floor against frequency: `python3 probe.py freq 200`, then ramp all 24 down.
      Where does the wall go dark? ____ % (it was about 27% at 1 kHz). Stop at once
      if it stutters.

## Part 3: at the controller box (two people, low voltage only)

Mains is at the lightboxes and wall sockets, not in this box. Don't open a lightbox.

- [ ] **Phono lead test.** Hold 19 on (wall dark). Pull one phono lead from a channel
      that should be on. Does that lightbox light at full? ____
      Pull more. Do the rest recover as leads come out? After how many? ____
- [ ] **Voltage at a phono socket** (centre pin to sleeve, DC volts):

      | State | Channel commanded on | Channel commanded off |
      |---|---|---|
      | All 24 on | ____ V | n/a |
      | 23 on | ____ V | ____ V |
      | 19 on | ____ V | ____ V |

- [ ] **The common red rail** on the stripboard, against ground:
      all on ____ V, 23 on ____ V, 19 on ____ V.
- [ ] Voltage at the box's round power socket: all on ____ V, 19 on ____ V.
- [ ] Phono sleeve common against the Pi's ground: ____ V (expect 0).
- [ ] Photos: stripboard top and underside, the power socket wiring, each PWM
      board's terminals. Read one transistor's markings ____ and one of each resistor's
      colour bands ____ / ____.
- [ ] Compare with the 2023 photo. Anything plugged in or wired differently? ____

## What the results mean

| Result | Conclusion | Next |
|---|---|---|
| Unplugged lead lights its box while the rest stay dark | Drivers and lightboxes are fine. Fault is in the controller box. | Use the voltage readings to find where |
| Unplugged lead stays dark | Fault is at the lightbox end or the mains feed | Stop and rethink. Check Part 1 results |
| "On" channel reads about 10 V with all on, but low with 19 on | The control side is dragging "on" channels down | Look at the rail |
| Red rail drops clearly between all-on and 19-on | The rail can't hold up. This is the fault | Check what feeds it: adapter rating, regulator, wiring |
| Rail steady, sockets still read low | The coupling is somewhere else (sleeve common, transistor wiring) | Trace from the photos |
| Power-on order changes the result | Something latches at power-up | Record which order works. Put it in the projectionist guide |
| Adapter label is lower voltage or current than the box needs | Likely cause | Find the right adapter before changing anything else |

## Loose ends from 2026-11-16

- Nextcloud: drafts for the folder (new README, updated quick reference, banners on
  the old notes) are drafted and waiting for Jonny's edits before they go up.
  The quick reference on Nextcloud and in the booth still shows the old buttons.
- Phone panel: `PHONE_PANEL_PLAN.md`. Open question is whether a page that can't
  darken the room is worth building.
- `authorized_keys` on the Pi has a broken first line and a blank line. Tidy up.
- Prune the old personal-hotspot Wi-Fi entries on the Pi.
- Map which lightbox is which LED number, and confirm it's 24 separate boxes.
- Later: fresh SD card with current Raspberry Pi OS. Keep today's card as the fallback.
