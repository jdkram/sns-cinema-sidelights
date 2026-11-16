---
human-contributors: ["Jonny Kram"]
---

# Hardware: what is known, and how

Earlier notes in this project stated guesses as facts and then built on them. So every line here carries its evidence. "Observed" means a person saw it at the cinema. "Photo" means it is visible in the October 2023 photos and videos on Nextcloud (`Tech > Cinema box lights > 0 - Project info`). "Read from code" means the 2018 software assumed it and the lights broadly work. "Inferred" means it follows from the above but nobody has looked.

## Signal path (inferred, needs one look at a lightbox to confirm)

```text
Booth buttons 1-5
      | long multi-core cable
      v
Controller box, central above the screen
   Raspberry Pi Zero W
      | I2C
   Two PCA9685 PWM boards (0x60 and 0x40), 12 channels used on each
      | 24 PWM signals, about 1 kHz
   24 small transistors, one per channel, two resistors each
      | 24 numbered phono (RCA) leads carrying a DIMMING SIGNAL, not power
      v
24 lightboxes, each with its own mains-powered Mean Well PWM-40-12
   The lead goes to the driver's dimming input; the driver powers the LEDs
```

Until November 2026 this file assumed one 40 W supply fed all 24 panels through the controller. The photos do not support that: the mains strips beside the screen carry a plug for every lightbox, and the leads leaving the controller are thin phono cables.

## Facts

| Fact | Evidence | Status |
|---|---|---|
| Two PCA9685 boards answer at 0x40 and 0x60 (0x70 is their shared "all-call" address) | `i2cdetect`, March 2026 | Observed |
| The controller holds a Pi Zero W, two PCA9685 boards, and 24 small three-legged transistors (TO-92) on stripboard, each with two resistors | Photo and video | Photo. Part numbers and resistor values not read |
| Each transistor is wired to the centre of a phono socket; all the sockets' outer contacts share one bare-wire rail | Photo | Photo |
| The phono leads are numbered with paper tags | Photo | Photo |
| The Pi connects through a removable multi-pin plug on its GPIO header. It was unplugged in October 2023 and refitted later | Video; Jonny's 2024 notes | Photo. Buttons and I2C work, so the plug is on the right pins for those |
| The controller has a round DC power socket, a regulator on an aluminium heatsink, and a multi-core cable to the booth through a gland | Photo and video | Photo. What feeds the power socket is unknown |
| Beside the screen, sockets labelled "DB3/2L3 LIGHTBOX ONLY" feed six-way strips full of plugs on yellow and white flex | Photo | Photo. Count of plugs not confirmed, but it is roughly one per lightbox |
| Left lights are powered from the left, right lights and the controller from the right | Jonny's 2024 notes | Reported |
| The lightboxes use Mean Well PWM-40-12 drivers (12 V, 3.34 A, 40 W, with a dimming input on a thin blue and white pair) | Label photo | Observed for one. One per lightbox is inferred |
| The panels are in two banks, left and right of the screen, each four rows of three | Jonny, November 2026 | Reported |
| All 24 panels light at 100%; all at 50% are steady | Session 004 | Observed |
| With all 24 ramped together, nothing is visible below about 27% | Session 004, one run, by eye | Observed once |
| One panel at 100% with the rest off: nothing, seen from right beside the panels with house lights off | Session 004; confirmed by Jonny, November 2026 | Observed, cause unknown |
| Two or three panels lit (KnightRider): nothing, including on the untouched 2018 program | Sessions 001, 003, 004 | Observed, cause unknown |
| All 24 at varied levels of 12-55% (Ember): nothing | Sessions 003, 004 | Observed, cause unknown |
| AmbientHigh looked like every panel rising and falling together, though each is sent a different level | Session 004 | Observed |
| The "Mexican wave" on button 5 used to work | Cinema wiki, before 2023 | Reported. So single panels could once be lit |
| A panel is lit while its PCA9685 pin is LOW | 2018 code | Read from code. Fits a transistor that pulls a dimming line low to turn a light off |
| LEDs 1-12 are on board 0x60, 13-24 on 0x40; channels 2-7 then 13 down to 8 | 2018 code | Read from code |
| Buttons 1-5 are on GPIO 22, 27, 18, 4, 17 (BCM); pressed reads HIGH | 2018 code; buttons work | Read from code |
| PWM frequency about 1017 Hz | 2018 code asks for 1000 Hz | Read from code |
| The Pi is a Zero W on Raspbian Stretch, Python 3.5.3, kernel 4.9 | Session 001 | Observed |

## Unknown

- **Whether each lightbox really has its own driver with the phono lead on its dimming wires.** One look inside or behind a lightbox settles it.
- **What feeds the controller's round power socket**, and what voltage the regulator produces.
- **Which transistors and resistors the controller uses.**
- **Which panel is which LED number.** The leads are numbered, so tracing a few will settle it.
- **Whether anything was put back differently** when the controller was refitted after 2023.

## Two explanations to test

Both are hypotheses. Both assume the signal path above.

**A. The dimming line rises slowly.** A Mean Well dimming input holds its own line high through a weak internal pull-up, and the controller's transistor pulls it low. Several metres of cable take time to charge back up through a weak pull-up. At 1 kHz a delay of about a quarter of a millisecond would swallow the bottom quarter of the brightness range, which is the 27% dark band. Test: lower the PWM frequency (`probe.py freq 200`) and see if the dark band shrinks in proportion. If it does, the fix is one number in `sidelights/config.py`.

**B. Something shared inside the controller sags.** Every channel has a second resistor, and there is a common red rail across the board. If those resistors pull the dimming lines up to a rail that cannot hold its voltage, then the more panels are being held off, the lower that rail drops, and the few panels meant to be lit get too weak a signal. That would explain why one panel alone stays dark, why all 24 together are fine, and why panels seem to move together. Test: measure the DC voltage at the controller's power socket with all panels on, then all off. A clear drop points here, and at whatever feeds that socket.

## Things earlier notes got wrong

Kept so nobody repeats them:

- **"One 40 W supply feeds all the panels and the controller switches its 12 V."** See above. Advice to replace "the" supply followed from this and should be ignored.
- **"The Mean Well's DIM wires are unconnected."** A misreading of one photo. If the signal path above is right, they are the whole control mechanism.
- **"The event engine cannot drive single channels."** The engine code has no such fault, and the test that bypassed the engine showed the same nothing.
- **"Use the PCA9685 full-on bit for 100%."** With this wiring full-on means pin HIGH, which is off. Tried and reverted in March 2026.
- **"If both boards show in `i2cdetect`, any remaining problem is software."** The bytes sent for one panel are the same whether or not other panels are lit.
