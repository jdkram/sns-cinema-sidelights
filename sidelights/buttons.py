# human-contributors: ["Jonny Kram"]
"""
buttons.py -- the five booth buttons.

Polled once per frame. A button counts as pressed after reading HIGH for
BUTTON_HOLD_SECONDS without a gap, and fires once per press. This is the same
rule the 2018 controller used.
"""

from . import config


class Buttons:

    def __init__(self) -> None:
        # Imported here so the preview and --no-buttons work without gpiozero.
        from gpiozero import DigitalInputDevice

        # pull_up=False: internal pull-down, so an open button reads LOW.
        self._inputs = [DigitalInputDevice(pin, pull_up=False) for pin in config.BUTTON_PINS]
        self._needed = max(1, int(round(config.BUTTON_HOLD_SECONDS * config.FPS)))
        self._count = [0] * len(self._inputs)
        self._fired = [False] * len(self._inputs)

    def poll(self) -> int | None:
        """Index (0 = button 1) of a button that has just been pressed, else None."""
        pressed = None
        for i, device in enumerate(self._inputs):
            if device.value:
                self._count[i] = min(self._count[i] + 1, self._needed)
                if self._count[i] >= self._needed and not self._fired[i]:
                    self._fired[i] = True
                    pressed = i
            else:
                self._count[i] = 0
                self._fired[i] = False
        return pressed
