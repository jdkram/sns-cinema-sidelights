# human-contributors: ["Jonny Kram"]
"""
The sidelight controller. Run from the repo folder:

    python3 -m sidelights                # normal: dark until a button is pressed
    python3 -m sidelights ember          # start a sequence straight away
    python3 -m sidelights --list         # sequence names, and what is on each button
    python3 -m sidelights --dry-run ember    # no hardware: print levels once a second

Only one program may drive the lights at a time. Stop the service before
running this by hand:    sudo systemctl stop sns-sidelights.service
"""

import argparse
import sys
import time

from . import config
from .engine import LEDManager
from .output import Output
from .sequences import SEQUENCES


def print_list() -> None:
    print("\nButtons:")
    for number, name in enumerate(config.BUTTON_SEQUENCES, 1):
        print("  %d  %s" % (number, name))
    print("\nAll sequences:")
    for name, cls in SEQUENCES.items():
        print("  %-14s %s" % (name, (cls.__doc__ or "").strip().splitlines()[0]))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sequence", nargs="?", help="sequence to start immediately")
    parser.add_argument("--list", action="store_true", help="list sequences and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="no I2C and no buttons; print levels once a second")
    parser.add_argument("--no-buttons", action="store_true", help="do not read the booth buttons")
    args = parser.parse_args()

    unknown = [name for name in config.BUTTON_SEQUENCES if name not in SEQUENCES]
    if unknown:
        sys.exit("config.py BUTTON_SEQUENCES names unknown sequences: %s" % ", ".join(unknown))
    if args.list:
        print_list()
        return
    first = args.sequence or config.STARTUP_SEQUENCE
    if first and first not in SEQUENCES:
        sys.exit("Unknown sequence '%s'. Try --list." % first)

    buttons = None
    if not (args.dry_run or args.no_buttons):
        try:
            from .buttons import Buttons
            buttons = Buttons()
        except Exception as error:  # missing gpiozero, or GPIO not available
            sys.exit("Cannot read the buttons (%s).\n"
                     "Install with: sudo apt install python3-gpiozero python3-lgpio\n"
                     "or run with --no-buttons." % error)

    leds = LEDManager()
    output = Output(dry_run=args.dry_run)
    current = None

    def start(name: str) -> None:
        nonlocal current
        print("Starting %s" % name, flush=True)
        # The LED values are deliberately not reset, so the new sequence fades
        # from wherever the last one left the lights.
        current = SEQUENCES[name](leds)
        current.start()

    print("Sidelights running. Buttons: %s" % ", ".join(config.BUTTON_SEQUENCES), flush=True)
    output.show(leds.state())
    if first:
        start(first)

    frame = 1.0 / config.FPS
    next_report = 0.0
    try:
        while True:
            began = time.monotonic()

            if buttons:
                pressed = buttons.poll()
                if pressed is not None:
                    print("Button %d" % (pressed + 1), flush=True)
                    start(config.BUTTON_SEQUENCES[pressed])

            if current:
                current.update()
            output.show(leds.state())

            if args.dry_run and began >= next_report:
                print(" ".join("%3d" % round(level) for level in leds.state()), flush=True)
                next_report = began + 1.0

            spare = frame - (time.monotonic() - began)
            if spare > 0:
                time.sleep(spare)
    except KeyboardInterrupt:
        print("\nStopped. The lights keep their last state.")


if __name__ == "__main__":
    main()
