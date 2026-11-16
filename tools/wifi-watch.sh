#!/bin/sh
# human-contributors: ["Jonny Kram"]
#
# Log Wi-Fi link quality on the Pi, to judge whether it holds a stable connection
# to the cinema AP from a given position. Needs no sudo. Logs to /tmp (RAM) so it
# doesn't wear the SD card and survives SSH dropping out (not a reboot).
#
# Start (keeps running after you disconnect):
#   nohup sh tools/wifi-watch.sh > /dev/null 2>&1 &
# Stop:      pkill -f wifi-watch.sh
# Read:      column -ts, /tmp/wifi-watch.csv | tail -30
# Summary:   sh tools/wifi-watch.sh --summary
#
# Columns: time, ssid, bssid (which AP), signal dBm, tx bitrate, ping loss % to the
# gateway (5 pings), average ping ms.
# Rough guide for signal: > -60 good, -60..-70 fine, -70..-80 marginal, < -80 bad.

LOG=${WIFI_WATCH_LOG:-/tmp/wifi-watch.csv}
INTERVAL=${WIFI_WATCH_INTERVAL:-15}

if [ "$1" = "--summary" ]; then
  awk -F, 'NR > 1 {
      n++; if ($2 == "") drop++
      if ($4 != "") { s += $4; ns++; if (min == "" || $4 < min) min = $4 }
      if ($6 != "") { loss += $6; nl++ }
      seen[$3]++
    }
    END {
      printf "samples %d, not associated %d\n", n, drop
      if (ns) printf "signal avg %.0f dBm, worst %d dBm\n", s / ns, min
      if (nl) printf "ping loss avg %.1f%%\n", loss / nl
      for (b in seen) printf "AP %s: %d samples\n", b, seen[b]
    }' "$LOG"
  exit
fi

[ -f "$LOG" ] || echo "time,ssid,bssid,signal_dbm,tx_bitrate,loss_pct,avg_ms" > "$LOG"

while :; do
  link=$(iw dev wlan0 link 2>/dev/null)
  ssid=$(echo "$link" | sed -n 's/^\s*SSID: //p' | tr ',' ' ')
  bssid=$(echo "$link" | sed -n 's/^Connected to \([0-9a-f:]*\).*/\1/p')
  signal=$(echo "$link" | sed -n 's/^\s*signal: \(-*[0-9]*\).*/\1/p')
  rate=$(echo "$link" | sed -n 's/^\s*tx bitrate: \([0-9.]*\).*/\1/p')
  gw=$(ip route | awk '/^default/ {print $3; exit}')
  loss=""; avg=""
  if [ -n "$gw" ]; then
    p=$(ping -c 5 -W 2 -q "$gw" 2>/dev/null)
    loss=$(echo "$p" | sed -n 's/.* \([0-9.]*\)% packet loss.*/\1/p')
    avg=$(echo "$p" | sed -n 's|^rtt [^=]*= [0-9.]*/\([0-9.]*\)/.*|\1|p')
  fi
  echo "$(date '+%F %T'),$ssid,$bssid,$signal,$rate,$loss,$avg" >> "$LOG"
  sleep "$INTERVAL"
done
