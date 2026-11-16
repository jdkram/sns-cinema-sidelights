---
human-authors: Jonny Kram
---

# Hardware Specifications: LED Driver

> **Corrected 2026-11-16** from the 2018 build photos. Earlier versions of this page said one driver fed all 24 panels with its DIM wires unused. Both were guesses and both were wrong. Fault summary and tests: [PSU_FAULT.md](PSU_FAULT.md).

**Each lightbox has its own Mean Well PWM-40-12** LED driver (24 in total), mounted on the lightbox's back panel with its own mains lead. It's an IP67 constant-voltage driver with a dimming input. The controller box doesn't power the lights. It sends each driver a dimming signal down a phono (RCA) lead.

Source: `Lightbox 00.JPG` to `Lightbox 24.JPG` (March 2018) in the Nextcloud folder `Archive/Build (2016-2019)/Basecamp docs/Rooms & Entrances/Cinema/Lightboxes/`, and the 2023 controller box photos in `Collective - Tech/Cinema box lights/0 - Project info/`. Not yet re-checked on site.

## Device Label Information

**Model:** Mean Well PWM-40-12  
**Type:** Class 2 Power Supply

### Specifications
- **Input:** 100-240V~ 0.6A 50/60Hz (277V~ for North America only: 0.25A 50/60Hz)
- **Output:** +12V…3.34A
- **IP Rating:** IP67 (Dust tight and waterproof)
- **Certifications:** SELV, CE, Double Insulated (Square-in-square symbol)

## Wiring Legend

| Wire | Function | Color | Notes |
|------|----------|-------|-------|
| **AC/L** | Live | BROWN | To the IEC inlet on the lightbox's green PCB |
| **AC/N** | Neutral | BLUE | To the IEC inlet on the lightbox's green PCB |
| **V+** | Positive Output | RED | To that lightbox's LED strip |
| **V-** | Negative Output | BLACK | To that lightbox's LED strip |
| **DIM+** | Dimming Control + | BLUE | Soldered to the lightbox's phono socket |
| **DIM-** | Dimming Control - | WHITE | Soldered to the lightbox's phono socket |

## Troubleshooting Notes

### Power and Connectivity
On each lightbox, the AC input (Brown/Blue) is wired into a small green PCB with an IEC inlet. If one lightbox is dead, check its mains lead first, then the solder joints or terminals on that green PCB first—they often take the most mechanical stress when the power leads are plugged and unplugged.

### Dimming Control
The DIM wires (Blue/White) go to a phono socket on the lightbox, and a phono lead runs from there to the controller box. The driver dims its own output according to what it sees on those wires: left open it runs at 100%, shorted it turns off, and a PWM signal gives a level in between. In the controller box each PCA9685 output drives a small transistor (through a resistor) that shorts or releases that lightbox's DIM pair.

A lightbox with its phono lead unplugged should therefore sit at full brightness whatever the Pi does. That's a handy test.

---

## Signal Path: Button Press to Light

```text
PROJECTION BOOTH
┌─────────────────┐
│  Button panel   │
│  [1] [2] [3]    │
│     [4] [5]     │
└────────┬────────┘
         │ wired cable run
         ▼
CONTROLLER BOX
┌─────────────────────────────────────────┐
│  Raspberry Pi Zero                      │
│                                         │
│  GPIO pins (BCM numbering)              │
│  btn1=22  btn2=27  btn3=18              │
│  btn4=4   btn5=17                       │
│       │                                 │
│       ▼  (wiringPi, BCM mode)           │
│  CDigitalButton                         │
│  press/release detection + debounce     │
│       │                                 │
│       ▼  wasPressed() fires             │
│  CSequenceManager                       │
│  BUTTON_SEQUENCE_MAP[i] → seq number    │
│       │                                 │
│       ▼  100 Hz update loop             │
│  Sequence events                        │
│  FadeEvent / BrightnessSetEvent /       │
│  PulseEvent → brightness 0-100          │
│       │                                 │
│       ▼                                 │
│  CLEDManager                            │
│  onTime = 4095 − (brightness×4095/100)  │
│  active-low: HIGH=off, LOW=on           │
│       │                                 │
│       ▼  pwmWrite() via wiringPi        │
│  ┌─────────┐       ┌─────────┐         │
│  │PCA9685  │       │PCA9685  │         │
│  │0x40     │       │0x60     │         │
│  │LEDs13-24│       │LEDs 1-12│         │
│  └────┬────┘       └────┬────┘         │
│       │  I2C bus        │              │
│       │  at 1000 Hz PWM │              │
└───────┼─────────────────┼──────────────┘
        │ PWM signal      │ PWM signal
        ▼                 ▼
  24× resistor + small transistor (TO-92)
  on stripboard: inverts the signal and
  shorts/releases one DIM pair each
        │
        ▼
  24× phono socket on the controller box
  (sleeves linked together: shared common)
        │
        │ 24× phono lead: dimming signal only
        │ (~10 V, microamps, from the driver)
        ▼
┌──────────────────────────┐
│ In EACH lightbox:        │
│ mains → IEC inlet PCB    │
│ → Mean Well PWM-40-12    │
│   (DIM+/DIM− from phono) │
│ → 12 V → its LED strip   │
└──────────────────────────┘
  × 24 lightboxes
```

### What this diagram clarifies

**The Mean Wells do the dimming.** The PCA9685 doesn't switch any 12 V. Its ~1 kHz PWM is a control signal, and each lightbox's driver turns that into brightness. Two PWM stages are involved (ours, then the driver's own output chopping), which is the likely reason low frequencies stutter.

**Active-low wiring.** `pwmWrite(0)` = lightbox fully on, `pwmWrite(4095)` = off. PCA9685 output high makes the transistor conduct, which shorts DIM and turns the driver off. Transistor type and resistor values haven't been read yet.

**Layout is unconfirmed.** The build photos show 24 separately numbered lightbox panels. Older notes here said "6 per box, 4 boxes". Check on site which is right.

**I2C is the software-to-hardware boundary.** Everything above the PCA9685 is software; everything below is hardware. If `i2cdetect -y 1` shows both boards (0x40 and 0x60) but sequences don't behave correctly, check the software first. Since session 006 (2026-11-16) we know there's also a real electrical fault below this line, see [PSU_FAULT.md](PSU_FAULT.md).

**wiringPi dependency.** The pca9685 library bundled in this repo (`pca9685/src/pca9685.c`, written 2014) is a wiringPi devLib extension. It registers the PCA9685 channels as virtual GPIO pins via `wiringPiNewNode`. This means the system wiringPi version matters: wiringPi was deprecated by its author in 2019, and behaviour differences have been observed on newer Raspberry Pi OS versions. If the Pi was re-flashed with a post-2019 Raspbian/Pi OS, this is a potential source of subtle breakage even if I2C itself is working.
