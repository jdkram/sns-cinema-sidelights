#!/bin/sh
# human-contributors: ["Jonny Kram"]
#
# Menu for trying the proposed button patterns one at a time (e.g. to film them).
# Run on the Pi (service stopped):   sh ~/sidelights/tools/pick.sh
# Press a number + Enter to switch. q + Enter to quit (lights hold last state).
#
# Shadow/colmap (column on/off) are left out on purpose: with the current PSU,
# switching columns makes the whole wall flash. Restore them after the PSU is replaced.

P=/home/pi/sidelights/tools/patterns.py

stop_pattern() {
  pkill -f "$P" 2>/dev/null
  sudo systemctl stop patterns-demo 2>/dev/null
  sleep 0.3
}

while :; do
  cat <<'EOF'

  Proposed button map (session 007)
  1  shimmer     pre-show ambience, irregular drift
  2  fadeout     off: 3 s fade to black
  3  breathe     slow regular pulse
  4  full        house lights, 100% (silent)
  5  countdown5  film starting: 5 dimming breaths, then black (~36 s)
  0  off (instant)
  q  quit
EOF
  printf '  > '
  read -r k || break
  case "$k" in
    1) n=shimmer ;; 2) n=fadeout ;; 3) n=breathe ;; 4) n=full ;; 5) n=countdown5 ;;
    0) stop_pattern; python3 /home/pi/sidelights/probe.py off; echo "  off"; continue ;;
    q|Q) stop_pattern; echo "  quit (lights hold last state)"; break ;;
    *) echo "  ?"; continue ;;
  esac
  stop_pattern
  python3 "$P" "$n" > /dev/null 2>&1 &
  echo "  now playing: button $k = $n"
done
