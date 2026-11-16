---
date: 2026-11-16
revised: 2026-11-16 (evening, after checking the 2018 build photos)
---

# Sidelights fault: summary for a circuits person

Written to hand to whoever looks at the hardware next. It separates what we
**observed** from what we **think**. Test detail: `sessions/006-hardware-truth.md`
(Results). Context: `sessions/007-cinema-wifi-and-hardening.md`.

> **Correction, 2026-11-16 evening.** The first version of this page said all 24
> panels were fed from one Mean Well PWM-40-12 and that the fix was a new power
> supply. That was never observed. It came from a diagram in `HARDWARE.md` that
> guessed at the wiring. The 2018 build photos show **one PWM-40-12 inside each
> lightbox**, dimmed by a signal lead from the controller box. **Do not buy a
> replacement supply.** The file keeps its old name so existing links work.

## System (from photos, not yet re-checked on site)

```
Pi Zero W → I2C → 2× PCA9685 (0x40, 0x60; 12 channels each, ~1 kHz)
          → 24× resistor + small transistor (TO-92) on stripboard
          → 24× phono (RCA) socket on the controller box
          → phono lead to each lightbox
          → that lightbox's own Mean Well PWM-40-12, DIM+ (blue) / DIM− (white)
          → that lightbox's LED strip (12 V, from its own driver)
```

- Each lightbox has its own driver, its own mains lead (IEC inlet on a small green
  PCB on the back panel) and its own phono socket. 24 drivers, 24 mains plugs.
- The controller box holds **no power supply for the lights and switches no 12 V**.
  It only sends a dimming signal. The phono sleeves are linked together inside the
  box with bare wire (a shared common).
- The PWM-40-12 is a dimming LED driver: DIM open = 100%, DIM shorted = off, or it
  follows a PWM signal on DIM. It supplies the dimming voltage itself (about 10 V,
  about 100 µA).
- Likely signal logic (inferred, fits the code): PCA9685 pin HIGH → transistor
  conducts → DIM shorted → lightbox **off**. Pin LOW → DIM open → lightbox **on**.
  That is the "active-low" behaviour, with no 12 V switching stage at all.

Evidence, all on the S&S Nextcloud:

- `Archive/Build (2016-2019)/Basecamp docs/Rooms & Entrances/Cinema/Lightboxes/`
  `Lightbox 00.JPG` to `Lightbox 24.JPG` (March 2018). `00` shows a whole back panel
  with the driver label. `24` shows the blue and white DIM wires soldered to the
  phono socket, next to the IEC inlet.
- `Collective - Tech/Cinema box lights/0 - Project info/IMG_20231020_161104.jpg`:
  controller box interior. `IMG_20231020_1553*.jpg` and `1556*.jpg`: the
  "LIGHT BOX ONLY" sockets and fully loaded extension strips.

## Observed (2026-11-16, channels held fully on/off, no PWM, unless stated)

- **All 24 on:** very bright, silent.
- **20–23 on:** all lit panels dim *together* to "mid"; audible hum (audible from
  the front rows, less so at row G). Where the hum comes from has not been located.
- **≤ 19 on:** nothing lights at all, including any single channel on either board.
- Depends on **how many** channels are on, not **which** (left column off = right
  column off).
- **All 24 under PWM at ~1 kHz:** 50% ≈ 70% perceived; 30% dim; 25% dark.
  At ~250 Hz, 25% lights but stutters irregularly.
- Panels set to **different** PWM levels mostly dim together.
- Both PCA9685 boards read back correctly and every channel switches as commanded.

## Not measured

No voltage readings anywhere. Transistor type and resistor values unread. The wiring
of the shared common not traced. Nobody has confirmed the 2018 wiring is unchanged.

## What this means

24 separate drivers can't affect each other through their 12 V outputs. So a fault
that depends on the **count** of channels, and dims everything **together**, has to
live in something they share:

1. **The control side in the controller box** (most likely): the shared common on the
   phono sleeves, its connection to the board's ground, or the transistor stage.
   Each "off" channel has a conducting transistor, so the fault grows with the
   number of channels that are off. That matches the cliff.
2. **The controller's own supply rail** sagging as more PCA9685 outputs go high.
3. **The mains feed** to the lightboxes (least likely: it doesn't change with what
   the Pi commands).

We do not have a confirmed mechanism. Treat the list as where to look, not as a
diagnosis.

**One model that fits every observation (untested):** the 24 dimming inputs are
behaving as if they were wired **in parallel**, and each conducting transistor can
only pull that shared line down part of the way. Then no channels off = full; one to
four off = the shared dimming voltage sags and every box dims together; five or more
off = it falls below the drivers' turn-on point and the wall goes dark. All 24 at the
same PWM level still works, because all the transistors switch together. 

**A physical candidate for that coupling** (from `HARDWARE.md` on the
`python-controller` branch, 2026-11-16 morning): the controller photo shows a
**second resistor on every channel and a common red rail** across the stripboard. If
those resistors pull each dimming line up to that shared rail, every "off" channel
draws current from it through its conducting transistor. A rail that can't hold its
voltage then sags as more channels are held off, and the channels meant to be on get
too weak a signal. What feeds that rail (the round power socket on the box, and any
regulator) is unknown.

Two facts say something changed rather than "it never worked": the cinema wiki
records that the "Mexican wave" pattern used to work before 2023, and the controller
box was opened and refitted around October 2023.

**Could it have been put back together wrong?** The box was reassembled around the
time the SD card was restored, so it's worth asking what a reassembly mistake could
and couldn't do:

- *Pi header or I2C ribbon reversed or shifted:* no. The Pi talks to both PCA9685
  boards, reads them back correctly, and the booth buttons work.
- *Phono leads in the wrong sockets:* no. That only changes which lightbox is which
  number.
- *The wrong power adapter in the box's round socket:* **yes, this would fit.** If
  the stripboard's common rail is fed from that socket and someone plugged in a
  lower-voltage or weaker adapter than the original, the rail would be marginal: fine
  with every channel on, sagging as channels are held off. Read the adapter's label
  (volts and amps) from the floor if the lead can be followed.
- *A power or ground wire to the stripboard left off or on the wrong pin* (for
  example the PCA9685 boards' V+ terminal, or the rail fed from the Pi's 3.3 V pin
  instead of 5 V): also fits, and the rail voltage reading below would show it.

It predicts something easy to check: **every phono socket reads the same voltage**,
whichever channels are commanded: about 10 V with all on, something in between with
23 on, near zero with 19 on.

## What would settle it (cheapest first)

1. **From the floor, no ladder.** Count the mains plugs in the "LIGHT BOX ONLY"
   strips on both sides (expect about 24). Unplug one: exactly one lightbox should go
   dark. That confirms one driver per box.
2. **At the controller box, no meter** (two people). Hold 19 on (whole wall dark,
   commands below). Pull out **one phono lead** from a channel that should be on.
   Its driver now sees DIM open, so that lightbox should go to full brightness on
   its own.
   - It lights → drivers and lightboxes are fine. The fault is inside the controller
     box. Pull more leads and see whether the remaining ones recover.
   - It stays dark → the problem is at the lightbox end or the mains feed.
3. **With a multimeter, DC volts, at a phono socket** (centre pin to sleeve; this is
   the dimming signal: about 10 V, microamps, safe to probe):

   | State | Expect | If not |
   |---|---|---|
   | All 24 on, any channel | about 10 V | That channel's lead or driver |
   | A channel commanded off | near 0 V | Transistor not conducting |
   | 19 on, a channel that should be **on** | about 10 V | **Low here = the control side is dragging "on" channels down. This is the fault.** |

   Then, in the all-on and 19-on states, measure the **common red rail** on the
   stripboard against ground (a clear drop at 19-on is the answer), the voltage at
   the box's round power socket, and the phono sleeve common against the Pi's ground.
4. While the box is open: photograph the underside of the stripboard, read one
   transistor's markings and one resistor's colour bands.

**Safety:** the controller box is low voltage only (5 V, 3.3 V, 10 V signal). Mains
is at each lightbox (IEC inlet on the back panel) and the wall sockets. Don't open a
lightbox while it's plugged in. The controller box is at height: **two people, never
alone.**

### Holding a test state from the Pi

```bash
ssh sns-sidelights
sudo systemctl stop sns-sidelights-py.service
cd ~/sidelights
python3 probe.py all 100                     # all 24 on (Ctrl+C; lights hold)
python3 -c "import probe as p; L=p.Lights(p.Bus()); L.set_all(100); [L.set(i,0) for i in range(1,6)]; L.show()"   # 19 on
sudo systemctl start sns-sidelights-py.service   # back to normal
```

## Glossary

- **PWM:** dimming by switching fully on/off fast. *Duty cycle* = % of each cycle on.
  30% at 1 kHz = on 0.3 ms, off 0.7 ms, 1000×/s.
- **PCA9685:** chip that generates 16 PWM signals itself. The Pi sets each duty cycle
  over **I2C** (a two-wire chip bus).
- **DIM+ / DIM−:** the driver's dimming input. The driver puts a small voltage on
  it and watches what the outside world does to it: left alone = full, shorted = off.
- **Active-low:** PCA9685 output LOW = lightbox on. The transistor in between
  inverts it.
- **Shared common:** all 24 dimming circuits return through one linked wire. If that
  path is poor, channels start to affect each other.
- **Why "count, not which" matters:** a bad channel fails specific panels. Panels
  failing below a total, and all dimming together, point at something **shared**.
