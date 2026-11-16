---
human-contributors: ["Jonny Kram"]
session-date: 2026-11-16
session-number: "007"
---

# Session 007: Cinema Wi-Fi, hardening, then the lights

**Date:** 2026-11-16
**Location:** Star and Shadow Cinema
**Laptop:** KUSANAGI (Linux Mint)
**Commit on Pi before session:** (`git -C /home/pi/sidelights rev-parse --short HEAD`)

Order matters. The Pi is about to sit on a shared network running an OS (Raspbian
Stretch, Debian 9) that has had no security fixes since 2022, so it's hardened
**before** it joins. Every risky change gets an `at` job that reverts it, in case it
cuts us off.

## How we work today

A local tmux session on KUSANAGI with `ssh` running inside it. It's driven with
`tmux send-keys` and read with `tmux capture-pane`. Jonny watches the same window
and types every sudo password himself. Nothing needs installing on the Pi for this.

```bash
sudo apt install -y tmux          # KUSANAGI, once
tmux new -s sns                   # Jonny, in a terminal he keeps visible
```

Pre-checked from KUSANAGI on the cinema Wi-Fi (2026-11-16):

- The Pi is **not** on the cinema LAN yet (no Raspberry Pi MAC seen, `raspberrypi.local` doesn't resolve).
- The cinema SSID broadcasts on 2.4 GHz (channels 1, 6, 11) in **WPA2/WPA3 transition**
  mode. Stretch's wpa_supplicant can't do WPA3, so it joins on WPA2. That works only if
  PMF is "optional", not "required". Check in UniFi before blaming the Pi.
- The SSID contains `*` and `&`. Always single-quote it in the shell.

---

## Phase 1: Get in over the hotspot

- [ ] Phone hotspot up as `sns_test` (2.4 GHz, WPA2). KUSANAGI joins it too.
- [ ] `ssh sns-sidelights` (or find the IP in the hotspot client list)
- [ ] Audit (read-only, no sudo): `ssh sns-sidelights 'sh -s' < tools/pi-audit.sh`
- [ ] Commit the Pi's HEAD and `git status` in the notes

## Phase 2: Harden (before joining the shared network)

1. **Password.** `passwd` (Jonny types it). Store it in the password manager, not here.
2. **Keys.** Make sure KUSANAGI's key and the home machines' keys are in
   `~/.ssh/authorized_keys`. Test key login in a **second** window before step 3.
3. **sshd: key-only, no root, only `pi`.** sshd uses the first match it finds, so the
   settings go at the top of the file:
   ```bash
   sudo cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.pre-007
   echo 'cp -a /etc/ssh/sshd_config.pre-007 /etc/ssh/sshd_config; systemctl restart ssh' | sudo at now + 10 minutes
   sudo sed -i '1i # session 007 (first match wins)\nPasswordAuthentication no\nChallengeResponseAuthentication no\nPermitRootLogin no\nAllowUsers pi\nX11Forwarding no\n' /etc/ssh/sshd_config
   sudo sshd -t && sudo systemctl restart ssh
   ```
   New window: key login works, and `ssh -o PubkeyAuthentication=no sns-sidelights` is refused.
   Then `sudo atrm <job>`.
4. **sudo.** Raspbian gives `pi` passwordless sudo (`/etc/sudoers.d/010_pi-nopasswd`).
   With that, a stolen laptop key is full root. Decide: remove it (sudo asks for the
   password) or keep it for convenience.
5. **Attack surface.** `sudo systemctl disable --now bluetooth hciuart` (nothing uses
   Bluetooth). Keep avahi (it's how `raspberrypi.local` works).
6. **Updates.** `sudo apt update && sudo apt full-upgrade` against the archive mirrors
   session 001 set up. This brings Stretch to its final state. There are no newer
   fixes to get, so unattended-upgrades is pointless on this OS (see "Later" below).
7. **Wi-Fi power saving off** (Pi Zero W drops SSH sessions with it on):
   `sudo iw dev wlan0 set power_save off`, and make it stick by adding
   `wireless-power off` under `wlan0` in `/etc/network/interfaces`.

## Phase 3: Join the cinema Wi-Fi (AP near the Pi)

```bash
sudo cp -a /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.pre-007
wpa_passphrase 'CINEMA_SSID' | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf
# type the Wi-Fi password + Enter. Then edit: delete the "#psk=" plaintext line,
# add priority=5 to the new block, and check the hotspot block has priority=10.
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
sudo wpa_cli -i wlan0 reconfigure
```

The hotspot stays at a higher priority, so on site with the hotspot on, the Pi prefers it.
Then turn the hotspot off, move KUSANAGI back to the cinema Wi-Fi, and find the Pi
(UniFi client list or `ping raspberrypi.local`).

- [ ] Joined. IP: ______ AP/BSSID: ______
- [ ] DHCP reservation on the BT Hub (it's the DHCP server). Reserved IP: ______
- [ ] Remote path works: `ssh -J weebo pi@<ip>` (and via weebo over Tailscale from off-site)

## Phase 4: Can it hold the link from the far side?

Start the logger with the AP still close, to get a baseline:

```bash
cd /home/pi/sidelights && nohup sh tools/wifi-watch.sh > /dev/null 2>&1 &
```

1. **Baseline, AP close:** 5 minutes. `sh tools/wifi-watch.sh --summary`
2. **Move the AP** to the far side of the auditorium. Expect SSH to drop while it
   reboots. The logger keeps running on the Pi.
3. Wait 2-3 minutes, reconnect, check the BSSID column to see which AP it chose.
   Then leave it **at least 15 minutes**, ideally with the auditorium in show conditions
   (projector on, doors shut, people in it if possible).
4. `sh tools/wifi-watch.sh --summary`

```
AP close:  signal avg ____ dBm  worst ____  loss ____ %
AP far:    signal avg ____ dBm  worst ____  loss ____ %  BSSID ____  dropouts ____
```

| Far-end result | Decision |
|---|---|
| Signal better than -70 dBm, loss under 1% | Good. Leave the AP on the far side. |
| -70 to -80 dBm or occasional loss | Usable for SSH. Consider moving the Pi's antenna side away from the metal box, or a different AP spot. |
| Worse than -80 dBm or it drops off | The AP needs to stay closer, or put a cheap USB Wi-Fi dongle / Ethernet on the Pi. |

If it drops off and doesn't come back, the hotspot (priority 10) is the way back in.

## Phase 5: The lights

Pick up session 006 (`sessions/006-hardware-truth.md`, Phase 2 tests with `probe.py`).
Remote access means these can now run from anywhere in the room, with someone else
watching the wall.

## Later (separate session): actually update the OS

Stretch can't be "updated" any further. The real fix is a fresh SD card with the current
Raspberry Pi OS Lite (32-bit, still supports the Zero W), set up in Raspberry Pi Imager
with the hostname, SSH key and cinema Wi-Fi. Then rebuild the controller there (WiringPi
fork, or the Python port), and keep **today's card as the rollback**. Do it on the bench,
then swap cards.

**Decided 2026-11-16:** no kernel upgrade on the Stretch card. 4.9 → 4.19 risks a Pi
that doesn't boot in an awkward location, and it would change the I2C/GPIO drivers mid
hardware-debugging. The new kernel comes with the reflash, once there's budget for a
high-endurance SD card and session 006's hardware tests are done.

## Results

```
Pi HEAD:              26b95b8 (behind main), stray untracked sidelights/ and
                      sns_cinema_sidelights/ copies inside the repo folder
Cinema IP / reservation: fixed (BT Hub reservation in the "servers" range; IP on Nextcloud)
Far-end verdict:      PASS. AP at back of auditorium: -52 dBm, 0% loss.
                      Meeting-room U6 Lite (through baffled walls): -65 dBm, 0% loss.
```

Far-end test detail (2026-11-16, `tools/wifi-watch.sh`, 15 s samples):

| AP | Samples | Avg | Worst | Loss |
|---|---|---|---|---|
| Back-of-auditorium AP (forced via `wpa_cli roam`) | 10 | -52 dBm | -53 | 0% |
| Meeting-room U6 Lite (chosen on its own) | 38 | -65 dBm | -66 | 0% |

With the AP beside it: -40 dBm (spot reading). Stretch's wpa_supplicant roams
lazily, so the Pi stays on whichever AP it joined first while the link is
decent. Either one is fine.

The upgrade finished cleanly (`EXIT=0`, no dpkg errors). It still needs a reboot to
load the new systemd and libc.

### Log (2026-11-16)

Audit before hardening (`tools/pi-audit.sh`):

- Pi Zero W, Raspbian Stretch, kernel 4.9.59, up 247 days, 37 °C, no throttling.
- Password was still the default. KUSANAGI's key was not installed.
- `pi` has passwordless sudo (`010_pi-nopasswd`).
- sshd allowed passwords, X11 forwarding on.
- `wpa_supplicant.conf` was world-readable. Saved networks: two old personal hotspots and
  `sns_test`. (Prune the personal hotspots.)
- apt lists last fetched September 2019. 183 upgrades pending.

Done:

- [x] KUSANAGI key installed (`ssh-copy-id`).
- [x] Password changed (in the password manager).
- [x] sshd: key-only, no root, `AllowUsers pi`, X11 off. Verified from a fresh
      connection: key works, password refused. Backup at `/etc/ssh/sshd_config.pre-007`.
- [x] `wpa_supplicant.conf` set to 600.
- [x] Bluetooth, hciuart, triggerhappy disabled.
- [x] Wi-Fi power saving off, persisted by `wifi-powersave-off.service`.
      (Don't add a `wlan0` block to `/etc/network/interfaces` on Stretch, because
      dhcpcd owns wlan0 and that can kill Wi-Fi at boot.)
- [x] `apt full-upgrade` (183 packages, run detached, log at `/var/log/apt-upgrade-007.log`).
      The kernel isn't in the legacy mirror, so it stays at 4.9.
- [x] Cinema Wi-Fi added at priority 5 (hotspots at 0, so they're a fallback).
- [x] Rebooted 14:42 UTC. Back in about 90 s on its reserved IP, on the back-of-auditorium AP
      at -52 dBm. Power save off, Bluetooth off, no failed units, PCA9685s at 0x40/0x60
      visible, service up.
- [x] Fixed `ExecStartPre=sleep 30` → `/bin/sleep 30` (on the Pi and in
      `config/systemd/`). Stretch's systemd 232 rejects relative paths, so it had been
      skipping the boot delay since March ("Executable path is not absolute, ignoring").
      After the fix: Starting 14:43:57 → Started 14:44:37.
- Remote access from off-site: jump through any tailnet PC (Jonny's call). No
  Tailscale on the Pi, no subnet route on weebo.

Decision: **passwordless sudo kept** (Jonny, 2026-11-16). This relies on the
laptops holding keys being secure, so a stolen laptop key means root on the Pi.
Revisit for the OS reflash.

Gotcha: `at` isn't installed on this image. Use
`sudo systemd-run --unit=revert-x --on-active=10min /bin/sh -c '...'` for revert
timers, and cancel with `sudo systemctl stop revert-x.timer`.
