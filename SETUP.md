---
human-contributors: ["Jonny Kram"]
---

# Setup and operation

How to build the Pi's SD card, get it on the network safely, and look after it. Written for someone comfortable copying commands into a terminal.

**These steps have not been run end to end yet.** They are step 3 of [PLAN.md](PLAN.md). Correct this file as you go the first time.

## What you need

- A new microSD card, 8 GB or more, a high-endurance one if possible
- A laptop with [Raspberry Pi Imager](https://www.raspberrypi.com/software/) and a card reader
- An SSH key on that laptop (`ssh-keygen -t ed25519` if you have none)
- The staff Wi-Fi name and password. It must offer 2.4 GHz with WPA2: the Pi Zero W cannot use 5 GHz
- A ladder and a second person, for swapping the card

Keep the old card. Label it "2018 C++, works" and leave it taped inside the controller box. Putting it back is the whole rollback plan.

## 1. Write the card

In Raspberry Pi Imager choose device **Raspberry Pi Zero** (the Zero W is covered by that entry), system **Raspberry Pi OS Lite (32-bit)**, then edit the settings before writing:

| Setting | Value |
|---|---|
| Hostname | `sidelights` |
| Username | `pi` |
| Password | A new strong one. Store it in the maintainers' password manager, not here |
| Wi-Fi | Staff network name and password, country GB |
| SSH | Enabled, **public-key authentication only**, paste your public key |

Key-only SSH means nobody can log in by guessing a password.

## 2. First boot

Do this on a bench or at home first if the Pi can be borrowed; otherwise in place. Give it two or three minutes, then:

```bash
ssh pi@sidelights.local
```

If the name does not resolve, find the Pi's address in the UniFi client list.

```bash
sudo raspi-config nonint do_i2c 0
```

```bash
echo "dtparam=i2c_arm_baudrate=400000" | sudo tee -a /boot/firmware/config.txt
```

```bash
sudo apt update && sudo apt install -y git i2c-tools python3-gpiozero python3-lgpio unattended-upgrades
```

```bash
git clone https://github.com/jdkram/sns-cinema-sidelights.git /home/pi/sidelights
```

```bash
sudo reboot
```

`unattended-upgrades` installs security fixes on its own. It does not reboot the Pi.

## 3. Check the hardware before the controller

With the Pi in the controller box and connected:

```bash
i2cdetect -y 1
```

Expect `40`, `60` and `70`.

```bash
cd /home/pi/sidelights && python3 probe.py info
```

```bash
python3 probe.py all 100
```

All 24 panels should light. Ctrl+C, then `python3 probe.py off`.

## 4. Run the controller by hand

```bash
python3 -m sidelights static75
```

The lights should come up steady. Press each booth button and watch both the lights and the terminal, which prints `Button 3` and `Starting heartbeat` as presses arrive. Ctrl+C to stop.

If presses do not register, or register on their own, that is the button inputs (the part of the controller least certain to work first time). Note what you see and run with `--no-buttons` meanwhile.

## 5. Start at boot

```bash
sudo cp config/systemd/sns-sidelights.service /etc/systemd/system/
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now sns-sidelights.service
```

Power-cycle the Pi and check the buttons work again without anyone logging in. The lights stay dark after boot until a button is pressed; set `STARTUP_SEQUENCE` in `sidelights/config.py` to change that.

## 6. Network access

- In UniFi or the BT Hub, give the Pi a reserved address so it does not move.
- Reach it from outside the building through the existing jump host: `ssh -J sns-weebo-tailscale pi@<pi-address>`. Nothing is installed on the Pi for this and no port is opened to the internet.
- Use the staff network, not the guest one. Guest networks stop devices talking to each other.
- The Pi offers one service to the network: SSH with keys. Keep it that way. If the IMS3000 trigger is done over the network (PLAN step 5), that listener must accept connections from the IMS3000's address only.
- To give another maintainer access, add their public key as a new line in `/home/pi/.ssh/authorized_keys`. To remove someone, delete their line.

## Day-to-day commands

| To do this | Run this on the Pi |
|---|---|
| See if it is running | `systemctl status sns-sidelights.service` |
| Read recent messages | `journalctl -u sns-sidelights.service -n 50` |
| Lights off now | `sudo systemctl stop sns-sidelights.service && python3 /home/pi/sidelights/probe.py off` |
| Bring it back | `sudo systemctl start sns-sidelights.service` |
| Try a sequence | Stop the service, then `cd /home/pi/sidelights && python3 -m sidelights ember` |
| Deploy a change | `cd /home/pi/sidelights && git pull && sudo systemctl restart sns-sidelights.service` |
| Shut down before pulling power | `sudo shutdown -h now` |

Only one program can drive the lights at a time. Stop the service before running `probe.py` or the controller by hand.

## Looking after it

- Every few months: `sudo apt update && sudo apt full-upgrade`, reboot, press all five buttons.
- The SD card is a consumable. If the Pi stops booting, a fresh card built from this page is the fix.
- The controller logs one line per button press, so the logs stay small.
- If the PCA9685 boards stop answering, the controller logs it once and keeps retrying. It does not need restarting when they come back.

## Going back to the old card

Shut down, swap the labelled 2018 card back in, power up. The old system does not know the staff Wi-Fi; it joins the phone hotspot it was set up with.
