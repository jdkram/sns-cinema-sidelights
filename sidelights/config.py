# human-contributors: ["Jonny Kram"]
"""
config.py -- everything that describes the installed hardware, in one place.

If a fact about the wiring changes or gets measured, change it here and in
HARDWARE.md. Nothing else in the package hard-codes hardware details.
"""

# --- PCA9685 boards ---------------------------------------------------------

I2C_BUS = "/dev/i2c-1"

# LEDs 1-12 are on the first board, 13-24 on the second.
BOARDS = (0x60, 0x40)

# PCA9685 channel for each of a board's 12 LEDs, in LED-number order. The
# second half of each board was wired in reverse in 2018.
CHANNEL_ORDER = (2, 3, 4, 5, 6, 7, 13, 12, 11, 10, 9, 8)

# True: a panel is lit while its PCA9685 output pin is LOW.
# Check with `python3 probe.py polarity`.
ACTIVE_LOW = True

# PWM frequency in Hz. The chip rounds this; 1000 gives about 1017 Hz, which
# is what the lights have always run at.
PWM_HZ = 1000

# Percent. 0 disables it. When above 0, brightness 0 stays off and 1-100 is
# stretched onto FLOOR-100. Leave at 0 until `probe.py ramp` shows the dark
# band is the same however many panels are lit; if it changes with the number
# of panels, the cause is shared hardware and this setting cannot fix it.
BRIGHTNESS_FLOOR = 0

# --- Buttons ----------------------------------------------------------------

# BCM GPIO numbers for booth buttons 1-5. Pressed = pin HIGH.
BUTTON_PINS = (22, 27, 18, 4, 17)

# Sequence name (from sequences.py) for booth buttons 1-5.
BUTTON_SEQUENCES = ("ambient", "fadeout", "heartbeat", "static75", "ambienthigh")

# A button must read pressed for this long before it counts. The cable run
# from the booth is long, so brief noise must not start a sequence.
BUTTON_HOLD_SECONDS = 0.1

# --- Playback ---------------------------------------------------------------

FPS = 50

# Sequence to start at boot, or None to stay dark until a button is pressed.
STARTUP_SEQUENCE = None
