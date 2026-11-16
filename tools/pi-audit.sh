#!/bin/sh
# human-contributors: ["Jonny Kram"]
#
# Read-only snapshot of the Pi's security and network state. Needs no sudo and
# changes nothing. Prints no secrets (no PSKs, no password hashes).
#
# Run from a dev machine:   ssh sns-sidelights 'sh -s' < tools/pi-audit.sh
# or on the Pi:              sh tools/pi-audit.sh

section() { printf '\n=== %s ===\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

section "System"
hostname
. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME"
uname -srm
cat /proc/device-tree/model 2>/dev/null; echo
uptime
df -h / /boot 2>/dev/null
free -h 2>/dev/null || free -m
vcgencmd measure_temp 2>/dev/null
vcgencmd get_throttled 2>/dev/null   # anything but 0x0 = undervoltage/throttling seen

section "Packages"
ls -l --time-style=long-iso /var/lib/apt/lists 2>/dev/null | sed -n '2p'   # last apt update
cat /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null | grep -v '^\s*#' | grep .
for p in tmux screen at iptables iptables-persistent fail2ban unattended-upgrades git i2c-tools; do
  printf '%-22s %s\n' "$p" "$(dpkg-query -W -f='${Status} ${Version}' "$p" 2>/dev/null | sed 's/install ok installed/installed/' || echo -)"
done

section "Accounts"
awk -F: '$7 !~ /(nologin|false|sync)$/ {print $1, $3, $7}' /etc/passwd
id
sudo -n true 2>/dev/null && echo "sudo: PASSWORDLESS for $(id -un)" || echo "sudo: needs a password"
ls /etc/sudoers.d/ 2>/dev/null

section "SSH"
dpkg-query -W -f='openssh-server ${Version}\n' openssh-server 2>/dev/null
grep -Ei '^\s*(PasswordAuthentication|ChallengeResponseAuthentication|KbdInteractiveAuthentication|PermitRootLogin|PubkeyAuthentication|AllowUsers|Port|X11Forwarding|Include)\b' /etc/ssh/sshd_config
echo "authorized_keys:"
[ -f ~/.ssh/authorized_keys ] && ssh-keygen -lf ~/.ssh/authorized_keys 2>/dev/null || echo "  (none)"

section "Listening sockets"
if have ss; then ss -tulnH 2>/dev/null || ss -tuln; else netstat -tuln; fi

section "Enabled services"
systemctl list-unit-files --type=service --state=enabled --no-legend 2>/dev/null | awk '{print $1}'
systemctl is-active sns-sidelights.service ssh atd avahi-daemon bluetooth hciuart 2>/dev/null | paste -sd' '

section "Wi-Fi"
iwgetid -r 2>/dev/null || echo "(not associated)"
ip -br addr 2>/dev/null || ip addr
ip route | head -3
iw dev wlan0 get power_save 2>/dev/null || iwconfig wlan0 2>/dev/null | grep -i 'power management'
echo "saved networks (wpa_cli; SSIDs only):"
wpa_cli -i wlan0 list_networks 2>/dev/null || echo "  (wpa_cli not permitted; needs netdev group or sudo)"
grep -E '^\s*(country|ssid|priority|key_mgmt|ieee80211w)' /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null \
  || echo "  (wpa_supplicant.conf not readable without sudo)"

section "Firewall"
have iptables && echo "iptables present (listing rules needs sudo)" || echo "no iptables binary"

section "Sidelights"
systemctl status sns-sidelights.service --no-pager 2>/dev/null | sed -n '1,5p'
if [ -d /home/pi/sidelights/.git ]; then
  git -C /home/pi/sidelights log -1 --format='HEAD %h %ad %s' --date=short
  git -C /home/pi/sidelights status --short | head -20
fi
crontab -l 2>/dev/null | grep -v '^#'
