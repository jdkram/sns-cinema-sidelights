---
date: 2026-11-16
status: plan only, nothing built
---

# Sidelights phone panel: plan

A small web page that lets a volunteer trigger the wall-light patterns from a phone,
alongside the five booth buttons. The buttons keep working exactly as now whatever
happens to the network or the page. Earlier thinking:
`Booth control UI and cinema lights - feasibility` in Jonny's notes (2026-10-10).

## In brief

- **Shape:** a second small Python process on the Pi (`tools/panel.py`, standard
  library only) serves one page and runs as an unprivileged user.
- **Interface:** it sends "press" messages to `tools/buttons.py` over a Unix socket
  and reads a status file the controller writes in `/run`.
- **Safety rules:** the pattern whitelist, the crossfade and the rate limit all live
  in the controller, so no trigger can get round them.
- **Auth:** a shared key carried in the link and a QR code posted inside the booth.
- **Phones can't darken the room** (decided 2026-11-16, see below). The page offers
  House lights up, Pre-show shimmer and Slow breathe. Fade to dark and the countdown
  stay on the booth buttons.

## 1. Options considered

| Option | Who can reach it | Auth | Verdict |
|---|---|---|---|
| A. HTTP thread inside `buttons.py` | Anyone on the cinema Wi-Fi | Shared key | Fewest files, wrong coupling |
| B. Separate `panel.py` plus Unix socket | Anyone on the cinema Wi-Fi | Shared key | **Recommended** |
| C1. Page on weebo relaying to the Pi | Same as B | Same as B | Adds a machine, solves nothing |
| C2. Buttons on lv426's Cloudflare Access page | Anyone on the internet who passes Access | Per-person, real TLS | Not now |

**Why not A.** It saves about 60 lines and one unit file, but the network-facing code
would run as `pi` (passwordless sudo, on an OS with no security fixes since 2022). A
crash in the web code would also take the buttons down for about 35 s, after which
the controller comes back at `full`, so the house lights rise mid-film.

**Why B.** One extra unit file and one system user. In return the controller never
reads network input, the web process holds no I2C, GPIO or sudo rights, and if it
dies the buttons carry on.

**Why not C2 yet.** It's the only option with real logins and TLS, but it needs a
path from the booth subnet to the Pi, depends on the internet and Cloudflare, and
makes the house lights controllable from off-site. B's endpoint is what lv426 would
call anyway, so B doesn't rule it out later.

**Auth without TLS.** The key is a random 20 to 22 character string in the link:
`http://<reserved-ip>:8080/?k=<key>`. It stays in the URL, so a bookmark or
home-screen icon carries it. Every request must include it. No lockout on bad keys
(a lockout would let a stranger lock volunteers out). Without the key the page says
only "Scan the QR code in the projection booth".

**What the key doesn't stop, and what follows from it.** The public can join the
Wi-Fi the Pi is on, and the page is plain HTTP, so anyone on it could capture the key
as a volunteer uses the page. The auditorium is very dark with the sidelights off
and the main lights down. Put together: a key that can be captured must not be able
to black out the room.

So the web side gets its own, shorter whitelist: `full`, `shimmer` and `breathe`
only. `fadeout` and `countdown5` are accepted from the booth buttons and from SSH,
never from the page. A captured key then lets a stranger swap between lit patterns,
slowly, and nothing else. Before building, check that the lowest point of `breathe`
and `shimmer` still leaves the room safely lit.

If darkening from a phone is wanted later, the route is signed requests: the key
stays in the part of the link after `#` (which browsers never send), and the page
signs each press with it together with a one-time number from the Pi. That's about
100 more lines, including a small SHA-256 in the page, because browsers don't offer
their built-in one over plain HTTP.

## 2. Control interface

**Commands.** A Unix datagram socket at `/run/sidelights/control.sock`. One short
text message per press: `<pattern> <source>`, e.g. `full phone`.

**One gate.** `buttons.py` already sends every change through `start()` and one
crossfade. Add a `request(name, source)` in front of it, used by both the button
poll and the socket:

1. The name must be in the `BUTTONS` table, else it's dropped. Column patterns aren't
   in that table, so nothing can reach them. A press from the page must also be in
   the lit-only list (`full`, `shimmer`, `breathe`).
2. Physical buttons are always accepted, exactly as now.
3. Other sources are refused within `WEB_MIN_GAP_S` (suggest 4 s, tune on the wall)
   of the last accepted change from any source.
4. `full` is exempt from rule 3. That can't cause flashing, because every downward
   change is still gated.
5. Last accepted press wins.

**Status.** The controller writes `/run/sidelights/status.json` on every change and
every 2 s as a heartbeat (it's in RAM, so no SD card wear): current pattern, what
triggered it ("button 3", "phone", "start"), whether it has finished, and when the
next web press will be accepted.

**HTTP.** Three routes, all needing the key: `GET /` (the page), `GET /status`,
`POST /press`. A button on the page only shows "On now" once `/status` says so.

**Isolation.** All the socket and status code in the controller sits inside
try/except. On an error it logs once and switches itself off. It must never break
the button loop.

## 3. The page

One static file, `tools/panel.html`, with inline CSS and about 60 lines of plain
JavaScript. No external resources, so it works with the internet down. Dark theme
only (a white page lights up the booth).

1. Status line: "Now: Slow breathe. Set from booth button 3, 2 minutes ago."
2. **House lights up**, first and largest, never disabled.
3. The other two, with the booth button number and a plain label:
   1 Pre-show shimmer; 3 Slow breathe.
4. A line of plain text: "To fade to dark or start the countdown, use buttons 2 and 5
   in the booth." The status line still reports those when the booth sets them.
5. Footer: "If this page stops working, use the buttons on the black box in the booth."

No confirm dialogs. The undo is "House lights up".

| State | What the volunteer sees |
|---|---|
| Sending | "Sending" on the pressed button |
| Hold-off | "Ready in 3 s" on the gated buttons |
| Changed elsewhere | "Changed from another phone" or "from the booth" |
| Connection lost | Banner: lights stay as they are, check you're on the cinema Wi-Fi, use the booth buttons |
| Controller down | "Lights controller is restarting" |
| Bad or missing key | "This link is out of date. Scan the code in the booth again." |

**Getting there.** A laminated card by the button box with the QR code, "join the
cinema Wi-Fi first", and what each button does. The key, IP and QR image stay out
of git (the repo is public).

**Accessibility (WCAG 2.1 AA).** Real `<button>` elements, at least 64 px tall and
full width. Near-white on near-black. The active pattern is shown by the words
"On now" plus a thick border, not by colour. Status in a `role="status"` region, the
connection banner `role="alert"`. Zoom allowed, reflows at 320 px, no animation.
Test with TalkBack and VoiceOver at 200% zoom.

## 4. When things go wrong

| Event | Result |
|---|---|
| Wi-Fi drops | Banner within about 6 s. The running pattern finishes on the Pi. Buttons unaffected. |
| Web service crashes | systemd restarts it. Lights and buttons untouched. |
| Controller crashes | Lights hold. After about 35 s it comes up at `full`. Same as today. |
| Pi reboots mid-show | About 90 s, then `full`. Same as today. |
| Two phones at once | Both see the same status within 2 s. First press wins; the second sees "Ready in N s" unless it was `full`. |
| Flood of requests | The web process is capped. Worst case the page is slow. |
| Key leaked | Change the key file, restart the web unit, print a new card. |

## 5. Build order

**Phase 1: control socket, status file, gate** (about half a day). About 100 lines
added to `buttons.py`, a small sender (`tools/press.py full`), unit tests for the
gate, and a `--sim` mode for `buttons.py` (fake lights, no GPIO) so it runs on a
laptop. Useful on its own: patterns can be triggered over SSH without stopping the
service. This is the only phase that touches the show-critical loop, so deploy it
between screenings and re-check all five buttons afterwards.

**Phase 2: `panel.py` and the page** (about a day), built on a laptop against
`--sim`. About 150 lines of Python and 200 of HTML. Testable off-site on a real phone.

**Phase 3: deploy** (about half a day plus a site visit). Create the user, add the
unit file and key file, test through an SSH tunnel first, then on site with an iPhone
and an Android. Print the card. Update `OPERATIONS.md` (it still recommends offline
mode), `SECURITY.md` and the Nextcloud projectionist guide.

**Not planned:** signed requests, an lv426 relay, or a cue from the film server. All
would reuse the same endpoint.

**To maintain it you'd need to know:** the controller listens on a socket and writes
a status file; the panel is one HTML file and three routes.

**Simulator.** Don't reuse `simulator/`. It models the old C++ engine and needs
Python 3.10+, where the Pi has 3.5.

## 6. Questions that change the design

Answered 2026-11-16 (Jonny):

- **The public can join the Wi-Fi the Pi is on.** So a shared key over plain HTTP
  can be captured. Hence the lit-only list above.
- **The auditorium is very dark with the sidelights off** when the main lights are
  down. No current fire risk assessment was found on Nextcloud (only build-era
  documents from 2016-2019, which don't mention the lightboxes). Worth asking
  whoever holds the current one before anything automated dims the room.

Still open:

1. **Should "House lights up" need the key?** Suggested: yes, with booth button 4 as
   the route that always works.
2. **Is control from outside the building wanted?** Assumed no.
3. **Who holds the card and the key?** Is "posted inside the booth only" acceptable
   as the rule for who may use it?
4. **Is a lit-only page still worth building?** The people who darken the room are
   in the booth, next to the buttons. If the main wish was a countdown from the
   stalls, signed requests move from "later" to phase 2.
