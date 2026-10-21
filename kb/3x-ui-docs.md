

=== SOURCE: https://docs.sanaei.dev
- 
- 

- 
- 

- 

# 3x-ui
Advanced web panel for managing Xray-core servers
Get startedView on GitHub
$`bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)`
stars47.7k stars
forks12.2k forks
latestv3.9.0 latest

## Everything you need to run Xray
A modern, fast control panel for Xray-core — built for operators who want power without the command-line grind.

### Every major protocol
VLESS, VMess, Trojan, Shadowsocks, WireGuard, Hysteria2, SOCKS, HTTP and Dokodemo-door — managed from one panel.

### REALITY & XTLS-Vision
First-class support for VLESS + REALITY with x25519 keys, short IDs and the xtls-rprx-vision flow for stealth and speed.

### Clients & traffic control
Per-client traffic quotas, expiry dates, IP limits and live online status, with one-click share links and QR codes.

### Multi-node & subscriptions
Coordinate multiple servers, managed hosts and external proxies, and serve VLESS / Clash / JSON subscriptions.

### Telegram & Discord bots
Built-in Telegram and Discord notifications for traffic caps, expiry warnings and system load, plus admin actions.

### Self-hosted & scriptable
A single Go binary or Docker image, an SQLite/PostgreSQL backend, and a full REST API for automation.


=== SOURCE: https://docs.sanaei.dev/docs/config/amneziawg
# AmneziaWG
Set up an AmneziaWG inbound in 3x-ui — obfuscation parameters, native IPv6, per-client port-forwarding, and routing client traffic through Xray.

AmneziaWG is a WireGuard fork that adds traffic obfuscation (junk packets,
randomized padding, and rewritten protocol magic values) so the tunnel doesn't
look like WireGuard to deep-packet inspection. It's a popular choice where
plain WireGuard is blocked but a WireGuard-shaped tunnel with a different
fingerprint gets through.

AmneziaWG runs embedded in the panel process — `amneziawg-go` over a
userspace (gVisor) network stack, not a kernel module. There is no DKMS
build, no Secure Boot conflict, and no host network/kernel access
requirement, so it works the same way inside a container as on bare
metal. Each peer's decapsulated traffic relays into its own loopback Xray
SOCKS5 inbound, so a peer's routing, sniffing, and per-client stats all
come from Xray's own machinery — the same as any other protocol's
inbound, not a separate code path.

## Key settings

### Server / interface

Field | What it is | 
Subnet | The tunnel's IPv4 subnet (e.g. `10.8.1.0/24`); each client gets an address from it. | 
MTU | Interface MTU. Leave at the default unless you have a reason to change it. | 
DNS (primary/secondary) | Seeded into downloadable client configs; the server's own interface doesn't need one. | 
External interface | The host NIC a peer's IPv6 address gets aliased onto when IPv6 is enabled (see below). Leave blank to auto-detect. | 

### Obfuscation (AmneziaWG 3.1)

The same values must match on both ends of the tunnel, so the server stores
them once and every client config inherits them. The panel generates a
randomized set for you (with a regenerate button) — a static, reused
value defeats the point, since DPI can fingerprint it over time.

Field | What it is | 
Jc | Number of junk packets sent before the handshake. | 
Jmin/Jmax | Size range (bytes) for those junk packets. `Jmin` must not exceed `Jmax`. | 
S1/S2 | Padding added to the handshake init/response packets, `0`-`1552` / `0`-`1608`: the packets are `148 + S1` and `92 + S2` bytes and must fit the 1700-byte receive buffer amneziawg-go uses on iOS. The panel also rejects `S1 + 56 = S2`, which would give both packets the same size on the wire (amneziawg-go itself accepts it). An AmneziaWG outbound takes the remote server's values as they are, up to `65535`. | 
S3 | Cookie-reply padding, `0`-`1636`: the reply is `64 + S3` bytes and must fit the 1700-byte receive buffer amneziawg-go uses on iOS. An outbound, as with S1/S2, takes the remote server's value up to `65535`. | 
S4 | Transport (data) packet padding, `0`-`32`. | 
H1-H4 | Header values that replace WireGuard's message-type field. Each is a single integer or a `low-high` range, and the four must not overlap — amneziawg-go and the kernel module refuse the whole device otherwise. `1`-`4` are WireGuard's own types and the engine default for a blank field: valid, but without a HeaderProtectionKey the type field then reads like plain WireGuard. | 
I1-I5 | Optional signature packets — random bytes prepended before the handshake, e.g. `<r 148>`. Generated sets fill `I1` only, matching Amnezia's own generator. | 
HeaderProtectionKey | A base64 32-byte key for the 3.0 header-protection mechanism. Must match on every client config; blank disables it. | 
ContentPaddingAddition | A single integer or `low-high` byte range of extra padding on content packets. Kept `<= 64` by the generator so a 1420-MTU tunnel doesn't fragment. | 
RekeyAfterTime / RekeyTimeout / RejectAfterTime / KeepaliveTimeout / MaxHandshakeAttempts | Handshake-timing randomization: each is a `low-high` range (seconds; attempts for the last one) the peer samples from, so session timing stops being a WireGuard fingerprint. Every `RekeyAfterTime` value must stay below every `RejectAfterTime` value. Blank keeps the WireGuard default. | 
RandomTrailers | Appends a random number of bytes to the end of every packet. | 
DisableCookies | Never send cookie replies — removes a DPI-visible WireGuard message type, at the cost of WireGuard's handshake-flood mitigation. | 

If you enter obfuscation values by hand instead of using the generated
defaults, keep `H1`-`H4` non-overlapping and above `4`, and double-check
`S1 + 56 != S2` — a bad value here keeps the embedded interface from
coming up at all.

The 3.1 parameters need a 3.1-capable client. Clients must run a
3.1-capable Amnezia app; blanking the 3.1 fields renders a config older
clients still understand. There is no host-side version requirement —
the panel ships its own pinned `amneziawg-go`, not whatever happens to be
installed on the system.

## Set it up in the panel

### Add an inbound
Add a new inbound, choose protocol AmneziaWG, and set the port and tunnel
subnet.

### Leave obfuscation on defaults (or regenerate)
The panel fills in a randomized, kernel-valid obfuscation set automatically.
Use Regenerate if you want a fresh one; there's no need to hand-edit these
unless you have a specific reason to.

### Add a client
Each client gets its own keypair and tunnel address. Download the client's
`.conf` or copy its share link (`vpn://…`, importable by the official
AmneziaWG/AmneziaVPN apps) from the client list.

### Optional: enable IPv6
Turning on IPv6 allocates an IPv6 address alongside each client's IPv4 one
from the configured IPv6 subnet. The panel aliases that address onto the
external interface's host NIC so outbound connections carry the peer's own
distinct public IPv6 identity — no NAT66 needed.

### Optional: forward ports to a client
Set a client's forwarded ports (e.g. `80, 443, 8000-8100`) to open a real
listener on the host that relays that traffic straight to the client's
tunnel address — useful for a client that needs to expose a service through
the server.

Every AmneziaWG inbound's traffic already goes through Xray — each peer
relays into its own loopback SOCKS5 inbound, tagged with the AmneziaWG
inbound's own tag, so it shows up as a normal source on the
Routing page like any other protocol's
inbound. There is no separate toggle for this: unlike a kernel tunnel,
there's no other way for a peer's traffic to reach the internet once it's
decapsulated.

## What the configuration looks like

A client's downloadable `.conf` (also what the `vpn://` share link encodes,
base64url'd) looks like this:

client .conf

`[Interface]
PrivateKey = <client private key>
Address = 10.8.1.2/32
DNS = 8.8.8.8, 8.8.4.4
Jc = 4
Jmin = 65
Jmax = 220
S1 = 87
S2 = 44
S3 = 21
S4 = 9
H1 = 463065432
H2 = 912345678
H3 = 1345678901
H4 = 1987654321
I1 = <r 148>
HeaderProtectionKey = 8Iu83eHDA3fMKKSGaEsVW9Ycd2lYYzc0MYlk1jJTvE4=
ContentPaddingAddition = 17-49
RekeyAfterTime = 111-139
RekeyTimeout = 4-7
RejectAfterTime = 187-251
KeepaliveTimeout = 9-14
MaxHandshakeAttempts = 19-36
RandomTrailers = on
DisableCookies = on

# my-client
[Peer]
PublicKey = <server public key>
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = your-server:443
PersistentKeepalive = 25`

## Multi-node (sub-nodes)

An AmneziaWG inbound can be created on, or cloned to, a sub-node. The node's
own panel runs the interface, so the node must run panel v3.7.0 or newer;
the master refuses an older node, or one that has not reported its version yet.
A client's `forwardedPorts` are checked against the ports in use on that node.

## Not yet covered

- Telegram bot — AmneziaWG inbounds haven't been exercised through the
bot yet. Treat it as unverified until someone reports back.


=== SOURCE: https://docs.sanaei.dev/docs/config/clients
# Clients
Manage 3x-ui clients — credentials, traffic and expiry limits, IP limits, groups, bulk actions, external links, and online status.

A client is a single user, identified by a unique email. In the current
panel, clients are first-class records that can be attached to multiple
inbounds at once, with per-client traffic accounting.

## Client fields

Field | Applies to | Meaning | 
Email | all | Unique identifier used for accounting and lookups. | 
ID (UUID) | VLESS, VMess, TUIC | The client credential. | 
Password | Trojan, Shadowsocks, TUIC | The client credential. | 
Auth | Hysteria2 | The client credential. | 
Flow | VLESS | XTLS flow, e.g. `xtls-rprx-vision`. | 
Limit IP | all (except TUIC) | Max simultaneous source IPs (enforced via Fail2ban). | 
Total (GB) | all | Traffic quota; the client is disabled when exhausted. | 
Expiry | all | Date after which the client stops working. | 
Auto renewal | all | Disabled, fixed interval in days, calendar weekly, or calendar monthly. | 
Telegram ID | all | Links the client to a Telegram user for self-service/notifications. | 
Sub ID | all | Subscription identifier grouping this client's links. | 
Group | all | Optional client group for organization and bulk filtering. | 
Comment | all | Free-text note. | 

Reaching the traffic or expiry limit disables the client, and a client
disabled or deleted by hand counts too; the panel restarts Xray then
(`restartXrayOnClientDisable`, on by default).

## Limits and IP control

- Traffic / expiry caps disable the client when hit; a Reset period
auto-renews the quota.

- Limit IP caps simultaneous source IPs. Enforcement relies on Fail2ban —
see Security. You can view a client's recent IPs
and clear them from the client's actions.

- Online status and last-online times are tracked per client (and per
node in multi-node setups).

## Automatic renewal

The individual and bulk-create forms offer one renewal mode at a time:

In the individual form, the mode, its day/weekday setting, and the renewal limit
share a row on desktop and stack on mobile. Help and the read-only preview use
the full width below them. The bulk-create form keeps its stacked fields. Help
follows the selected mode; the day-1/month-end note appears only for monthly
renewal. Independent traffic-reset settings remain separate.

Mode | API fields | Schedule | 
Disabled | `reset=0`, `resetDay=0`, `resetWeekday=0` | The expiry is not renewed. | 
Fixed interval | `reset=N`, other two fields `0` | Add exactly N × 24 hours to the previous cutoff. | 
Calendar weekly | `resetWeekday=1..7`, other two fields `0` | Renew at panel-local midnight on Monday (1) through Sunday (7). | 
Calendar monthly | `resetDay=1..31`, `resetWeekday=0` | Renew at panel-local midnight on that day; missing dates clamp to the month's last day without losing the configured day. | 

Calendar weeks stay on the selected weekday across daylight-saving changes;
they are not equivalent to a fixed seven-day interval. A skipped midnight uses
the first valid instant of that date; a repeated midnight uses the first one.
If a timezone skips the entire selected date, the next matching week is used.
Existing monthly clients
that also have `reset` set retain monthly precedence. The API rejects weekly
renewal combined with a positive `reset` or `resetDay`.

For a full calendar month, select monthly, day 1 and set the initial cutoff
to the next month's first midnight. For example, `2030-09-01 00:00:00` is valid
through `2030-08-31 23:59:59`. Day 31 renews at the start of the 31st and is
not the same schedule. The existing optional month-end subscription-header
display remains a separate setting and is not enabled by this form.

The preview uses the panel's timezone and the same calendar/catch-up calculation
as automatic renewal. It shows the cutoff, last valid second, next expiry, and
allowances needed. It is informational: it does not save, activate, reserve, or
guarantee a future renewal. When no expiry is set, auto-renewal cannot run; an
explicit button can set the first calendar cutoff. Selecting a mode alone never
rewrites an existing expiry. First-use clients keep their initial duration, and
their calendar dates are available after activation.

Preview dates use the Gregorian format `YYYY-MM-DD HH:mm:ss UTC±HH:mm`,
preserving any fractional seconds in the cutoff. Each date includes its own
UTC offset, so a daylight-saving change can show different offsets before and
after renewal. The heading identifies the panel time zone; Server local time
means the server's `Local` setting, not the browser's time zone. For example,
`2026-09-27 05:00:00 UTC+00:00` is 13:00 in UTC+08:00. Estimated renewals used
is the allowance this preview would consume, including any catch-up periods,
not a count of renewals already performed. The first-cutoff button uses the same
date format; clicking it still requires saving the form to persist the change.

For legacy last-second calendar cutoffs, the renewal boundary includes the
existing free alignment to the following midnight. The last-valid-second
preview still uses the stored expiry, not that alignment: an exclusive
`23:59:59` cutoff is valid through `23:59:58`. Use a next-midnight cutoff for
full-day validity; the preview itself does not repair the initial expiry.

`resetMax=0` means unlimited renewals. A positive limit counts each elapsed
period, including offline catch-up, not each scheduler tick or attached inbound.
If the remaining allowances cannot reach a future cutoff, the client stays
expired and its traffic is not reset. Operator-disabled clients stay disabled.

Renewal already resets client traffic. The separate periodic traffic reset
does not move the expiry and is unchanged; keep it disabled unless you intend an
additional reset. Quarterly, yearly, and every-N-week/month schedules are not
part of these modes.

Upgrade the main panel and every participating node before enabling weekly
renewal. Older versions ignore `resetWeekday`; a weekly-only client would not
auto-renew and, after its expiry or quota is exhausted, can be deleted by
delete depleted clients because older versions lack the weekly protection.
Back up the database and convert weekly schedules to a renewal mode supported
by every participating version before downgrading. Merely disabling weekly
renewal does not protect a depleted client from deletion. Avoid depleted-client
cleanup while a mixed-version fleet or unconverted weekly clients remain.
Database upgrades default this new field to `0` and preserve existing limits
and dates.

## Share links and external links

Every client has share links and a QR code for its inbounds, plus a combined
subscription. You can also attach external
links to a client — extra `vless://`, `vmess://`, `trojan://`, `ss://`,
`hysteria2://`, or `wireguard://` links, or a remote subscription URL — so they
appear alongside the panel-generated ones in the client's subscription.

To inspect exactly what a link contains, paste it into the
share-link inspector.

## Bulk actions

For managing many clients at once, the panel supports bulk create, enable,
disable, delete, attach/detach (to inbounds), reset traffic, and
adjust (add days / add bytes / set flow). Maintenance actions also let you
delete depleted clients (quota/expiry exhausted) and orphaned clients
(not attached to any inbound).

A client's share link contains its credential. Treat links and QR codes like
passwords, and rotate the credential if one leaks.


=== SOURCE: https://docs.sanaei.dev/docs/config/inbounds
# Inbounds & Protocols
Create inbounds in 3x-ui — protocols, transports, traffic reset and expiry, and fallbacks that serve multiple protocols on one port.

An inbound is a listener that accepts client connections on a port using a
particular protocol and transport. Most of your day-to-day work is creating and
managing inbounds and the clients inside them.

## Create an inbound

### Add an inbound
Open Inbounds → Add, give it a remark, pick a protocol, and choose a
port and listen address.

### Choose a transport and security
Pick the transport (TCP, WebSocket, gRPC, HTTPUpgrade, XHTTP, …) and the security
layer (none, TLS, or REALITY). See Transports and
REALITY.

### Add clients
Add one or more clients, each with its own credential, limits, and share link.
See Clients.

### Set traffic limit, expiry, and reset
Optionally cap total traffic and set an expiry date for the inbound, and choose a
periodic traffic reset schedule: `never` (default), `hourly`, `daily`,
`weekly`, or `monthly`.
For `monthly` resets, select a day from 1 to 31. If the selected day does not
exist in a shorter month, the reset runs on that month's last day.

## Supported protocols

The inbound editor accepts these protocols:

Protocol | Notes | 
VLESS | Lightweight; the basis for REALITY + XTLS-Vision. Recommended. | 
VMess | Older but very widely supported by clients. | 
Trojan | TLS-based; supports XTLS and fallbacks. | 
Shadowsocks | Includes Shadowsocks-2022 (`2022-blake3-*`) ciphers. | 
WireGuard | Modern tunnel. | 
AmneziaWG | Obfuscated WireGuard fork, embedded in the panel process. See AmneziaWG. | 
Hysteria2 | Selected as `hysteria`; the panel emits `hysteria2://` links. | 
HTTP | HTTP proxy. | 
Mixed (SOCKS/HTTP) | A combined SOCKS + HTTP listener. | 
Dokodemo-door / Tunnel | Port forwarding / traffic redirect. | 
MTProto | Telegram MTProto proxy, served by a bundled `mtg` process (not Xray). | 
TUIC | QUIC-based proxy protocol (v5), served by an in-process native Go server. See TUIC. | 

Hysteria2 isn't a separate protocol internally — it's the `hysteria` protocol
with the transport version set to 2, and the panel generates `hysteria2://`
share links for it.

## Fallbacks — multiple protocols on one port

Fallbacks let a single TLS port (e.g. `443`) serve more than one protocol — for
example VLESS and Trojan — by routing unmatched handshakes to a child
inbound. In 3x-ui, fallbacks are managed in the panel (a master inbound's
Fallbacks list) rather than hand-written into JSON.

Fallbacks are available only when the master inbound is:

- VLESS or Trojan,

- on the raw TCP transport,

- with TLS or REALITY security.

Each fallback rule targets a child inbound and can match on `path`, `alpn`, and
`dest`. Client share links for a fallback child are automatically rewritten to
advertise the master's address, port, and TLS.

## Not sure which to pick?

Use the wizard to get a recommendation based on your goals and clients:

### 

Primary goalCensorshipGeneralSpeed
Censorship levelHighMediumLow
Client supportModernBroad

Recommended
VLESSWebSocketTLS
VLESS + WebSocket + TLS is a flexible, CDN-friendly default for everyday use with modern clients.
Transports →Inbounds →

For censorship resistance with modern clients, VLESS + REALITY +
XTLS-Vision is the usual best choice — continue to
REALITY.


=== SOURCE: https://docs.sanaei.dev/docs/config/panel
# Panel Settings
Every 3x-ui panel setting — web server, TLS, display, security, and notifications — with defaults from the source.

Panel Settings controls how the panel itself is served and secured (separate
from your inbounds and clients). Settings are stored as key/value pairs; the
defaults below come straight from the panel source. Secrets (tokens, passwords)
are shown only as a "set / not set" indicator and are never returned to the
browser in full.

## Web server

Setting | Default | Meaning | 
`webPort` | `2053` | Panel port (1–65535). The `XUI_PORT` env var overrides it at runtime. | 
`webListen` | (all interfaces) | Bind the panel to a specific IP. | 
`webBasePath` | `/` | URL path the panel is served under (always normalized to `/…/`). | 
`webCertFile` / `webKeyFile` | (none) | TLS certificate + key. When both are set, the panel serves HTTPS. | 
`sessionMaxAge` | `360` | Session lifetime in minutes (default 6 hours). | 
`trustedProxyCIDRs` | `127.0.0.1/32,::1/128` | IPs/CIDRs whose forwarded headers (real client IP) are trusted. A custom value also controls forwarded host and scheme in subscription links; include the subscription proxy or set `subURI` to override those links. | 
`panelOutbound` | (none) | Route the panel's own egress (update checks, Telegram, geo/sub fetches) through a named Xray outbound. | 

After changing the port or base path, the panel URL becomes
`http(s)://<server>:<port><web-base-path>`. You can preset the base path on first
launch with `XUI_INIT_WEB_BASE_PATH`.

### TLS

Serving the panel over HTTPS protects your credentials in transit. Either set
`webCertFile` + `webKeyFile` — the `x-ui` SSL menu
can obtain a Let's Encrypt certificate for you — or terminate TLS at a
reverse proxy.

Never expose the panel over plain HTTP on the public internet. Use TLS, a
non-default port, and a long random web base path.

## Display

Setting | Default | Meaning | 
`pageSize` | `25` | Rows per page in lists (`0` disables pagination). | 
`expireDiff` | `0` | Days before expiry to start warning. | 
`trafficDiff` | `0` | Percent of quota remaining at which to start warning. | 
`remarkTemplate` | `{{INBOUND}}-{{EMAIL}}|📊{{TRAFFIC_LEFT}}|⏳{{DAYS_LEFT}}D` | Default client remark template (see Share links). | 
`timeLocation` | `Local` | Time zone for stats and expiry. | 
`datepicker` | `gregorian` | Calendar for date inputs (Gregorian or Jalali/Persian). | 

## Security & authentication

Credentials, two-factor auth, the brute-force limiter, sessions, and LDAP are
covered in First login and
Security. In short:

- Passwords are stored as bcrypt hashes; changing them logs out all sessions.

- 2FA (TOTP) can be required at login.

- An LDAP fallback can authenticate users when the local password check fails.

- API access uses API tokens managed under Panel Settings (see the
API reference).

## Notifications & subscription

These have their own settings groups and pages:

### Telegram bot
Token, chat IDs, alerts, and reports.

### Discord bot
Token, channel ID, and event alerts.

### Subscription
Subscription server, formats, and paths.

### Security
2FA, IP limits, and hardening.

Email (SMTP) notifications are also configurable (host, port, encryption,
recipients) with the same event types as the Telegram bot.


=== SOURCE: https://docs.sanaei.dev/docs/config/reality
# REALITY
Set up a VLESS + REALITY inbound with XTLS-Vision in 3x-ui — keys, short IDs, SNI, fingerprints, and common pitfalls.

REALITY is an Xray transport security that disguises your proxy as ordinary
traffic to a real, popular website. Unlike classic TLS, your server needs no
certificate of its own — it borrows the TLS handshake of the target site
(`dest`). Combined with the XTLS-Vision flow, it is fast and resistant to
deep-packet inspection.

REALITY is used with VLESS (and Trojan). The recommended flow is
`xtls-rprx-vision`.

## Key settings

When you choose REALITY as the security mode on a VLESS inbound, 3x-ui
exposes these fields:

Field | What it is | 
Dest (target) | A real TLS site to impersonate, e.g. `www.microsoft.com:443`. | 
SNI / Server Names | The hostname(s) clients send; must match the target's certificate. | 
Public / Private key | An x25519 keypair. The private key stays on the server. | 
Short IDs | Hex strings used to authenticate clients (you can have several). | 
Flow | Set to `xtls-rprx-vision`. | 
Fingerprint (uTLS) | The client TLS fingerprint to mimic, e.g. `chrome`. | 

The private key is generated with Xray's `x25519` utility (the panel can
generate the pair for you):

generate an x25519 keypair

`xray x25519`

## Set it up in the panel

### Create a VLESS inbound
Add a new inbound, choose protocol VLESS, and set Security to
reality.

### Choose a target (dest) and SNI
Pick a reputable site that supports TLS 1.3 and HTTP/2 and is reachable from your
server and your clients (for example `www.microsoft.com:443`). Set the server
names / SNI to match that site's certificate.

### Generate keys and short IDs
Generate the x25519 keypair and one or more short IDs. Keep the private key
secret; clients only ever receive the public key.

### Set the flow and fingerprint
Use the `xtls-rprx-vision` flow and a common uTLS fingerprint such as `chrome`.

### Add a client and share the link
Create a client, then use its share link or QR code in a compatible app
(v2rayNG, Hiddify, Mihomo, and others).

## What the configuration looks like

On the server, a REALITY inbound's `streamSettings` looks roughly like this:

server inbound (excerpt)

`{
 "network": "tcp",
 "security": "reality",
 "realitySettings": {
 "dest": "www.microsoft.com:443",
 "serverNames": ["www.microsoft.com"],
 "privateKey": "<x25519 private key>",
 "shortIds": ["<hex short id>"],
 "fingerprint": "chrome"
 }
}`

The matching client share link carries the public parameters:

vless:// (excerpt)

`vless://<uuid>@<server>:443?security=reality&pbk=<public-key>&sid=<short-id>&sni=www.microsoft.com&fp=chrome&spx=%2F&flow=xtls-rprx-vision#my-reality`

- `pbk` — REALITY public key

- `sid` — short ID (matches one on the server)

- `sni` — server name (matches the target's certificate)

- `fp` — client fingerprint

- `spx` — spiderX path

- `flow` — `xtls-rprx-vision`

## Common pitfalls

- Bad target. The `dest` must be a real site that supports TLS 1.3 and
HTTP/2, is reachable, and isn't blocked in your region. Pick a site you do
not own and that sees lots of traffic.

- SNI mismatch. The SNI / server names must match the target's real
certificate, or the handshake gives the disguise away.

- Leaked private key. Only ever distribute the public key to clients.

- Wrong flow. REALITY + XTLS-Vision needs `flow = xtls-rprx-vision` on both
the inbound client entry and the share link.

- Client version limits. Xray-core v26.9.8+ no longer sets a minimum when
Min Client Ver is empty. An explicitly saved minimum still applies. Earlier
builds may use a built-in minimum (such as `26.3.27`), rejecting third-party
clients even with correct keys. Check the running core version before changing
this gate; lowering it also admits older fingerprints.

- Mihomo and ML-KEM. Xray-core v26.9.8+ independently requires an
`X25519MLKEM768` key share before the optional `X25519` share. The Clash/Mihomo
YAML subscription enables `reality-opts.support-x25519mlkem768` for REALITY
nodes, including external links, and uses `chrome` when no fingerprint was set.
Explicit fingerprints are preserved: choose one that offers ML-KEM (`chrome`
with Mihomo's uTLS v1.8.7); enabling the flag cannot upgrade an old fingerprint.
Raw `vless://` links carry the equivalent `support-x25519mlkem768=true` hint;
clients that support this URI extension, including current Mihomo builds, apply
it on import. Very old REALITY servers that reject ML-KEM require a per-node
client override setting this option to `false`, or a server upgrade. Clearing
the version limit alone does not fix the handshake.

## Generate a config

Use the generator below to create a fresh X25519 keypair, UUID, and short ID,
then copy the server inbound JSON and the client share link. Everything is
computed in your browser — no keys or links are sent anywhere.

### 

Server addressYour domain or IP
Port
Dest (camouflage target)A real TLS 1.3 site, e.g. www.microsoft.com:443
SNI / Server name
Fingerprintchromefirefoxsafariiosandroidedgerandom
Generated keys & identifiers

Public key``
Private key``
UUID``
Short ID``

Server inbound (Xray JSON)
``

Client share link
``

The private key belongs only on your server. Share the generated
`vless://` link (which contains the public key) with clients.


=== SOURCE: https://docs.sanaei.dev/docs/config/share-links
# Share Links
3x-ui share-link formats (vless, vmess, trojan, ss, hysteria2, mtproto), the remark template variables, and an in-browser link inspector.

3x-ui generates a share link (and QR code) for each client. Client apps such
as v2rayNG, Hiddify, and Mihomo import these links to configure themselves.

## Link formats

Scheme | Shape | 
`vless://` | `vless://<uuid>@<host>:<port>?<params>#<remark>` | 
`vmess://` | `vmess://<base64-json>` (a base64-encoded JSON object) | 
`trojan://` | `trojan://<password>@<host>:<port>?<params>#<remark>` | 
`ss://` | `ss://<userinfo>@<host>:<port>?<params>#<remark>` (SIP002; Shadowsocks-2022 uses percent-encoded userinfo) | 
`hysteria2://` | `hysteria2://<auth>@<host>:<port>?<params>#<remark>` | 
`tg://proxy` | `tg://proxy?server=…&port=…&secret=…` (MTProto) | 
`tuic://` | `tuic://<uuid>:<password>@<host>:<port>?<params>#<remark>` (TUIC v5) | 

The query parameters carry the transport and security settings — `security`,
`sni`, `fp`, `pbk`, `sid`, `spx`, `flow`, `type`, `path`, `host`, `alpn`, and
more.

## Inspect a link

Paste any share link to decode every field. Parsing happens entirely in your
browser — the link is never sent over the network.

### 

Share links contain everything needed to connect as a client, including the
client's credential. Treat them like passwords.

## Remark template variables

The text after `#` in each link (the remark) is generated from a template
you control in Panel Settings (`remarkTemplate`). The default is:

`{{INBOUND}}-{{EMAIL}}|📊{{TRAFFIC_LEFT}}|⏳{{DAYS_LEFT}}D`

Tokens use `{{UPPER_CASE}}` syntax. The template is split on `|` into segments;
a segment whose only value is the unlimited marker `∞` (for `TRAFFIC_LEFT`,
`TRAFFIC_TOTAL`, `DAYS_LEFT`, or `TIME_LEFT`) is dropped, so unlimited clients
don't show empty decorations.

### Available tokens

Token | Value | 
`{{EMAIL}}` / `{{USERNAME}}` | Client email (identifier) | 
`{{INBOUND}}` | Inbound remark | 
`{{HOST}}` | Host-row remark (managed hosts) | 
`{{ID}}` / `{{SHORT_ID}}` | Client UUID / its first 8 chars | 
`{{TELEGRAM_ID}}` · `{{SUB_ID}}` · `{{COMMENT}}` | Telegram ID, subscription ID, comment | 
`{{STATUS}}` / `{{STATUS_EMOJI}}` | `active`/`expired`/`depleted`/`disabled` (or ✅⏳🚫) | 
`{{DAYS_LEFT}}` / `{{TIME_LEFT}}` | Days, or `Xd Xh Xm`, remaining (`∞` if unlimited) | 
`{{EXPIRE_DATE}}` / `{{JALALI_EXPIRE_DATE}}` / `{{EXPIRE_UNIX}}` | Expiry as Gregorian / Jalali date / Unix seconds | 
`{{CREATED_UNIX}}` | Creation time (Unix seconds) | 
`{{TRAFFIC_USED}}` / `{{TRAFFIC_LEFT}}` / `{{TRAFFIC_TOTAL}}` | Human-readable usage (`∞` if unlimited) | 
`{{TRAFFIC_USED_BYTES}}` / `{{TRAFFIC_LEFT_BYTES}}` / `{{TRAFFIC_TOTAL_BYTES}}` | Same, in bytes | 
`{{UP}}` / `{{DOWN}}` | Upload / download (human-readable) | 
`{{RESET_DAYS}}` · `{{USAGE_PERCENTAGE}}` | Reset period (days) · used percent | 
`{{PROTOCOL}}` / `{{TRANSPORT}}` / `{{SECURITY}}` | e.g. `VLESS` / `ws` / `REALITY` | 

Usage tokens (traffic, days, status) appear in the subscription body but
are stripped from the display/QR view, so a shared QR doesn't leak a client's
remaining quota. Date tokens follow the `datepicker` setting (Gregorian or
Jalali).

## Related

### REALITY
Generate a VLESS + REALITY config and link.

### Subscription
Serve all of a client's links from one URL.


=== SOURCE: https://docs.sanaei.dev/docs/config/ssl-certificates
# SSL Certificates
Get and renew TLS certificates for the 3x-ui panel and inbounds — with the x-ui ACME menu (domain or bare IP), a Cloudflare DNS-01 wildcard, or manual Certbot.

A TLS certificate lets you serve the panel over HTTPS (so your login and API
traffic are encrypted) and terminate TLS on inbounds (VLESS-TLS, Trojan,
Shadowsocks-TLS, and friends). There are three ways to obtain one:

- The `x-ui` menu — built-in ACME
client. Easiest for a single domain or a bare IP.

- Cloudflare DNS-01 — also from the menu; needed for wildcard certs or
when port 80 is blocked / the server sits behind Cloudflare's proxy.

- Manual Certbot — if you'd rather manage `acme.sh`/Certbot yourself.

If you put the panel behind Nginx or Caddy, let the proxy handle the
certificate instead — see Reverse proxy.
REALITY inbounds need no certificate at all; they
borrow a real site's TLS. This page is for the panel and for classic TLS
inbounds.

## The `x-ui` SSL menu (Let's Encrypt)

Run `x-ui` and choose `20` — SSL Certificate Management. It drives
acme.sh and offers:

Option | What it does | 
Get SSL (Domain) | Issue a certificate for a domain via HTTP validation. | 
Get SSL for IP Address | Issue a short-lived (6-day, auto-renewing) cert for a bare IP. | 
Revoke | Revoke an existing certificate. | 
Force Renew | Renew now, before expiry. | 
Show Existing Domains | List certificates already on the server. | 
Set Cert paths for the panel | Point the panel's TLS at an issued cert (sets the fields for you). | 

### Issue a certificate for a domain

### Point the domain at the server
Create an `A` (and/or `AAAA`) record for your domain that resolves to this
server's public IP. Validation fails until DNS has propagated.

### Free up port 80
HTTP validation needs port 80 reachable from the internet and not already in
use. Stop anything bound to it for the duration, and allow it through the
firewall.

### Run the issuer
`x-ui` → `20` → Get SSL (Domain), then enter the domain. acme.sh requests
the certificate and saves it under `/root/cert/<domain>/` as `fullchain.pem`
(the certificate chain) and `privkey.pem` (the private key).

### Wire it into the panel
Choose Set Cert paths for the panel to fill in `webCertFile` and
`webKeyFile` and restart the panel, or set them yourself in
Panel Settings. The panel serves HTTPS as soon as both
are set.

### Issue a certificate for a bare IP

No domain? Choose Get SSL for IP Address to obtain a short-lived
certificate (valid ~6 days, renewed automatically) bound to the server's IP.
Useful for reaching the panel over HTTPS before you've set up a domain.

## Cloudflare (DNS-01 wildcard)

DNS validation proves you control the domain by creating a TXT record instead of
answering on port 80 — so it works behind Cloudflare's proxy, on servers
where port 80 is blocked, and for wildcard certificates (`*.example.com`).

Your domain's DNS must be managed by Cloudflare, and you need one of:

- a scoped API token with the `Zone:DNS:Edit` permission (recommended), or

- your account email + Global API Key.

### Create a scoped API token
In the Cloudflare dashboard go to My Profile → API Tokens →
Create Token, pick the
Edit zone DNS template, scope it to the zone you're issuing for, and create
it. Copy the token — it's shown only once.

### Run the Cloudflare issuer
`x-ui` → `21` — Cloudflare SSL Certificate. When asked, choose `t` for an
API token (the default) or `g` for the Global API Key, then enter your
domain (and, for the Global API Key, your account email and key). acme.sh creates
the TXT record, validates, and cleans it up.

### Point the panel at it
As with the domain flow, use Set Cert paths for the panel (menu `20`) or set
`webCertFile` / `webKeyFile` in Panel Settings.

Prefer a scoped token over the Global API Key — it only grants DNS edits on the
zone you choose, so a leak can't touch the rest of your Cloudflare account.

## Manual (Certbot)

If you'd rather not use the menu, issue a certificate with Certbot's standalone
plugin (again, this needs port 80 free and the domain resolving to the server):

`apt-get install certbot -y
certbot certonly --standalone --agree-tos --register-unsafely-without-email -d yourdomain.com
certbot renew --dry-run`

Certbot writes the certificate to `/etc/letsencrypt/live/yourdomain.com/`
(`fullchain.pem` and `privkey.pem`). Point the panel at those two files in
Panel Settings, and set up renewal — `certbot renew`
runs on a systemd timer by default.

## Using the certificate

- Panel — set `webCertFile` (the full chain) and `webKeyFile` (the private
key) in Panel Settings. Both must be set for the
panel to switch to HTTPS. Menu option `11` — View Current Settings prints
the paths currently in use.

- Inbounds — when you enable TLS on an inbound, reference the same
certificate and key files (or paste their contents) in the inbound's TLS
settings. See Inbounds and
Transports.

Certificates expire (Let's Encrypt: 90 days; IP certs: ~6 days). The menu and
Certbot both renew automatically, but the panel keeps reading the files at
their fixed paths — so renew in place rather than moving the files, and the
panel picks up the new cert on its next restart. Force Renew (menu `20`)
triggers a renewal on demand.

## Next steps

### Panel Settings
webCertFile / webKeyFile and the rest of the web-server settings.

### Reverse proxy
Let Nginx or Caddy terminate TLS for you instead.

### REALITY
Stealth TLS for inbounds — no certificate required.


=== SOURCE: https://docs.sanaei.dev/docs/config/subscription
# Subscription
Run the 3x-ui subscription server — base64/JSON/Clash formats, ports and paths, TLS, response headers, and custom templates.

A subscription is a single URL that returns all of a client's
configurations. Client apps refresh it periodically, so when you change an
inbound, clients pick up the change automatically. The subscription server runs
as a separate server from the panel.

## Enable and configure

The subscription server is on by default (`subEnable`). Configure it in the
panel's subscription settings:

Setting | Default | Meaning | 
`subPort` | `2096` | Listen port (separate from the panel). | 
`subListen` | (all) | Bind address. | 
`subPath` | (random per panel) | Base path for raw subscription URLs. | 
`subDomain` | (none) | Public host; if set, the server only answers for that Host. | 
`subCertFile` / `subKeyFile` | (none) | TLS cert + key — when set, the server serves HTTPS. | 
`subEncrypt` | `true` | Base64-encode the raw subscription body. | 
`subUpdates` | `12` | Suggested refresh interval (hours) sent to clients. | 

A subscription URL looks like:

`https://<sub-host>:<sub-port>/<sub-path>/<sub-id>`

where `<sub-id>` is the client's Sub ID.

The same Sub ID is served in several formats on different paths — the Base64
list at `subPath` and the JSON (Xray-json) config at the JSON path. Build the
URLs and preview both bodies here:

### 

Schemehttpshttp
Host
Port
Sub ID
Sub path
JSON pathBehind a reverse proxy (omit the port)

Base64 subscription URL
`https://sub.example.com:2096/your-sub-path/user-1`

JSON subscription URL
`https://sub.example.com:2096/your-json-path/user-1`

#### Clients in this subscription

Protocolvlessvmesstrojanss
Remark
Address
Port
UUID (id)
Transporttcpkcpwsgrpchttpupgradexhttp
Securitynonetlsreality
SNI

Subscription links (decoded body)
`vless://11111111-2222-3333-4444-555555555555@a.example.com:443?type=tcp&security=reality&sni=www.microsoft.com#HK-01`

Base64 body
`dmxlc3M6Ly8xMTExMTExMS0yMjIyLTMzMzMtNDQ0NC01NTU1NTU1NTU1NTVAYS5leGFtcGxlLmNvbTo0NDM/dHlwZT10Y3Amc2VjdXJpdHk9cmVhbGl0eSZzbmk9d3d3Lm1pY3Jvc29mdC5jb20jSEstMDE=`

JSON subscription (preview)
`{
 "remarks": "HK-01",
 "dns": {
 "tag": "dns_out",
 "queryStrategy": "UseIP",
 "servers": [
 {
 "address": "8.8.8.8",
 "skipFallback": false
 }
 ]
 },
 "inbounds": [
 {
 "listen": "127.0.0.1",
 "port": 10808,
 "protocol": "socks",
 "settings": {
 "auth": "noauth",
 "udp": true,
 "userLevel": 8
 },
 "sniffing": {
 "destOverride": [
 "http",
 "tls",
 "quic",
 "fakedns"
 ],
 "enabled": true
 },
 "tag": "mixed"
 },
 {
 "listen": "127.0.0.1",
 "port": 10809,
 "protocol": "http",
 "settings": {
 "userLevel": 8
 },
 "tag": "http"
 }
 ],
 "log": {
 "loglevel": "warning"
 },
 "policy": {
 "levels": {
 "8": {
 "connIdle": 300,
 "downlinkOnly": 1,
 "handshake": 4,
 "uplinkOnly": 1
 }
 },
 "system": {
 "statsOutboundUplink": true,
 "statsOutboundDownlink": true
 }
 },
 "routing": {
 "domainStrategy": "AsIs",
 "rules": [
 {
 "type": "field",
 "network": "tcp,udp",
 "outboundTag": "proxy"
 }
 ]
 },
 "stats": {},
 "outbounds": [
 {
 "protocol": "vless",
 "tag": "proxy",
 "streamSettings": {
 "network": "tcp",
 "security": "reality",
 "tcpSettings": {
 "header": {
 "type": "none"
 }
 },
 "realitySettings": {
 "fingerprint": "chrome",
 "serverName": "www.microsoft.com"
 }
 },
 "settings": {
 "address": "a.example.com",
 "port": 443,
 "id": "11111111-2222-3333-4444-555555555555",
 "encryption": "none",
 "level": 8
 }
 },
 {
 "tag": "direct",
 "protocol": "freedom",
 "settings": {
 "domainStrategy": "AsIs",
 "redirect": "",
 "noises": []
 }
 },
 {
 "tag": "block",
 "protocol": "blackhole",
 "settings": {
 "response": {
 "type": "http"
 }
 }
 }
 ]
}`

## Output formats

The format is chosen by path, each with its own enable toggle:

Format | Path | Enabled by | Output | 
Raw links | `subPath` | always (if on) | A list of `vless://`, `vmess://`, … links (base64-encoded when `subEncrypt` is on). | 
JSON | `subJsonPath` | `subJsonEnable` | Full Xray client config(s). | 
Clash / Mihomo | `subClashPath` | `subClashEnable` | Full Mihomo-compatible YAML profile. | 
Mihomo (explicit) | `/mihomo/` | `subClashEnable` | Alias for the full `subClashPath` profile. | 
Clash for Windows (legacy) | `/clash-legacy/` | `subClashEnable` | YAML limited to proxy types, transports, and ciphers supported by the legacy Clash core. | 

Only enabled inbounds using VLESS, VMess, Trojan, Shadowsocks, WireGuard, AmneziaWG, MTProto, TUIC, or Hysteria2
appear in a subscription, ordered by their sub-sort index (TUIC and AmneziaWG are included in raw links and Clash/Mihomo profiles, but omitted from JSON endpoints; MTProto is included in raw links). Requesting `subPath`
with an `Accept: text/html` header (or `?html=1`) returns a human-readable info
page instead of the raw body.

Use `/mihomo/<sub-id>` for Clash Verge Rev, Mihomo, and other maintained
Mihomo-based clients. Use `/clash-legacy/<sub-id>` only for the discontinued
Clash for Windows client. The legacy endpoint keeps compatible VMess, Trojan,
and Shadowsocks nodes and excludes VLESS, Hysteria2, Reality, XHTTP,
HTTPUpgrade, and Shadowsocks 2022. If no compatible node exists, it returns an
explicit `422` response instead of a YAML profile the client cannot import.
To avoid Mihomo-only syntax entering the legacy profile, this endpoint always
uses its minimal `PROXY` group and `MATCH,PROXY` rule and ignores custom Clash
routing settings.

If an administrator has already assigned `/mihomo/` or `/clash-legacy/` to a
different configurable subscription path, that existing path is preserved and
the conflicting alias is skipped with a warning at startup.

Automatic Clash format detection keeps the existing `(?i)(clash|mihomo)`
default matcher so existing subscription URLs continue returning YAML.
It does not distinguish legacy clients from Mihomo-based clients; Clash for
Windows users must use `/clash-legacy/<sub-id>` for a compatible profile.

### Base64 vs JSON

The Base64 body is just the newline-joined share links, standard-base64
encoded (toggle with `subEncrypt`). The JSON body wraps each client in a
complete Xray client config — a fixed skeleton (local SOCKS/HTTP inbounds bound to 127.0.0.1, DNS,
routing, policy) plus a `proxy` outbound pointing at the inbound. 3x-ui emits a
single config object for one client and an array for several, uses the flat
outbound `settings` form (`address`/`port`/`id`, `level: 8`), and strips
`sockopt` from `streamSettings`.

## Response headers

Subscriptions return standard headers that compatible apps read:

- `Subscription-Userinfo` — `upload`, `download`, `total` (bytes; `total=0`
means unlimited) and `expire` (Unix seconds).

- `Profile-Update-Interval` — refresh interval in hours (`subUpdates`).

- `Profile-Title`, `Support-Url`, `Profile-Web-Page-Url`,
`Announce` — optional branding shown by some clients.

### Profile page links and upgrades

In Subscription → Profile → Profile page, choose `subProfileMode` for all
subscription clients:

- No link (`none`, default): omit `Profile-Web-Page-Url`.

- Built-in subscription page (`builtin`): link to the client's built-in page.

- Custom website (`custom`): use `subProfileUrl`; a blank URL omits the header.

Upgrade note: previously, an empty `subProfileUrl` automatically linked to
the built-in page. After upgrading, an unset mode with an empty or whitespace-only
URL becomes No link; an existing nonempty URL remains a Custom website.
To restore the built-in link, select Built-in subscription page above and
save the settings.

The built-in page exposes subscription URLs and node configurations, including
for Happ encrypted subscriptions. Enable it only if you intend to provide that
access.

### Optional month-end expiry display

Under Subscription → Information, Month-end subscription expiry display
(`subCalendarExpireInclusive`, default `false`) reports the last valid second
of the month in `Subscription-Userinfo` instead of the next month's midnight.
It applies only when every client contributing to the subscription has calendar
renewal day `1`, shares the same fixed expiry, and that expiry is exactly day `1`
at `00:00:00` in the configured panel timezone, immediately after the previous
month's last second. A later repeated midnight during a DST rollback is not
converted. Raw, JSON, Mihomo, and legacy
Clash subscriptions use the same conversion.

For example, the real cutoff `2030-10-01 00:00:00` is presented as
`2030-09-30 23:59:59`. The stored expiry, access cutoff, traffic accounting,
renewal schedule, remark expiry variables, and HTML/JSON info-page cutoff stay
unchanged. Arbitrary times, other renewal days, interval renewal, first-use
durations, unlimited expiries, mixed renewal modes, and different cutoffs are
not converted.

This is an opt-in compatibility tradeoff, not a change to expiry semantics by
default: apps receive a timestamp one second before the real cutoff and may
consider the subscription expired one second early. Apps format it in their own
timezone; matching the panel timezone is needed to display the same month-end
date. Cached subscription information changes only after the app refreshes it.

## Custom page templates

Point `subThemeDir` at a folder containing a custom info-page template to brand
the HTML subscription page. The per-client remark on each link is fully
templated — see Share links → remark variables.

Put the subscription server behind TLS (set `subCertFile`/`subKeyFile`, or a
reverse proxy) so subscription contents
aren't exposed in transit.


=== SOURCE: https://docs.sanaei.dev/docs/config/transports
# Transports & Security
Every transport 3x-ui exposes — TCP, mKCP, WebSocket, gRPC, HTTPUpgrade, XHTTP, Hysteria — with their settings, plus FinalMask obfuscation, sockopt, TLS/REALITY, XTLS-Vision, and VLESS encryption.

A transport decides how packets are carried between client and server, a
security layer decides how they're encrypted and disguised, and FinalMask
can obfuscate what's left. The panel only offers valid combinations; this page
lists every transport's settings and the rules the panel enforces.

## Transports

Pick the transport (the inbound's `network`) in the inbound/outbound form. Each
network writes its own settings key on the wire (`tcpSettings`, `kcpSettings`, …).

Transport | Settings key | When to use it | 
TCP (Raw) | `tcpSettings` | Lowest overhead. The basis for REALITY + XTLS-Vision and fallbacks; optional HTTP/1.1 header camouflage. | 
mKCP | `kcpSettings` | Reliable protocol over UDP — trades bandwidth for lower latency on lossy links. Carries no TLS/REALITY. | 
WebSocket | `wsSettings` | Works through CDNs and HTTP reverse proxies; very compatible. | 
gRPC | `grpcSettings` | HTTP/2-based; multiplexes well and proxies cleanly through Nginx. | 
HTTPUpgrade | `httpupgradeSettings` | CDN-friendly HTTP/1.1 `Upgrade`; lighter than full WebSocket. | 
XHTTP | `xhttpSettings` | Modern stream-multiplexed HTTP transport; CDN-friendly and REALITY-capable. | 
Hysteria | `hysteriaSettings` | QUIC-based transport — only for the Hysteria2 protocol. | 

WireGuard and Tunnel (dokodemo-door) inbounds expose no transport
selector — their stream carries only security/sockopt. Earlier panels also
exposed a raw HTTP/2 (`http`) transport; it has been superseded by XHTTP
and is no longer selectable.

### TCP (Raw) — `tcpSettings`

Field | Default | Meaning | 
`acceptProxyProtocol` | `false` | Accept the PROXY protocol from an upstream proxy so the real client IP is preserved. | 
`header.type` | `none` | `none`, or `http` for HTTP/1.1 camouflage. | 
`header.request` / `response` | — | When `type: http`: method, path, version and a header map that mimic a normal HTTP exchange. | 

### mKCP — `kcpSettings`

Field | Default | Meaning | 
`mtu` | `1350` | Maximum transmission unit, in bytes (576–1460). | 
`tti` | `20` | Transmission time interval, in ms (10–100). Lower = more responsive, more overhead. | 
`uplinkCapacity` | `5` | Upload bandwidth budget, in MB/s. | 
`downlinkCapacity` | `20` | Download bandwidth budget, in MB/s. | 
`cwndMultiplier` | `1` | Congestion-window multiplier; raise to push harder on good links. | 
`maxSendingWindow` | `2097152` | Upper bound on in-flight packets. | 

mKCP can't carry TLS or REALITY. To disguise it, add a FinalMask UDP mask —
the `mkcp-legacy` mask reproduces the classic header obfuscation that older Xray
stored in `kcpSettings.header`/`seed` (those fields no longer exist here).

### WebSocket — `wsSettings`

Field | Default | Meaning | 
`path` | `/` | Request path — route on it when several services share one host. | 
`host` | (none) | `Host` header override (useful behind a CDN). | 
`headers` | `{}` | Extra request headers. | 
`heartbeatPeriod` | `0` | Seconds between keepalive pings; `0` disables them. | 
`acceptProxyProtocol` | `false` | Accept the PROXY protocol from an upstream. | 

### gRPC — `grpcSettings`

Field | Default | Meaning | 
`serviceName` | (none) | gRPC service path; acts like a secret route. | 
`authority` | (none) | `:authority` pseudo-header override. | 
`multiMode` | `false` | Multiplex several streams over one connection. | 

### HTTPUpgrade — `httpupgradeSettings`

Field | Default | Meaning | 
`path` | `/` | Request path. | 
`host` | (none) | `Host` header override. | 
`headers` | `{}` | Extra request headers. | 
`acceptProxyProtocol` | `false` | Accept the PROXY protocol from an upstream. | 

HTTPUpgrade is a one-shot HTTP/1.1 `Upgrade` with no WebSocket framing — there's
no heartbeat field.

### XHTTP — `xhttpSettings`

XHTTP (SplitHTTP) has a large field set; the panel fills sensible defaults. The
ones you'll usually touch:

Field | Default | Meaning | 
`path` | `/` | Request path. | 
`host` | (none) | `Host` header override. | 
`mode` | `auto` | `auto`, `packet-up`, `stream-up`, or `stream-one`. `packet-up` is the most CDN-compatible; `stream-*` are lower latency. | 
`xPaddingBytes` | `100-1000` | Random padding range that blurs packet sizes. | 
`scMaxBufferedPosts` | `30` | Server-side buffer for uploaded POSTs. | 
`scStreamUpServerSecs` | `20-80` | Stream-up server window (dash range). | 
`xmux` (`enableXmux`) | (off) | Connection multiplexing — `maxConcurrency` `16-32`, `maxConnections` `6`, … Turn on for high concurrency. | 

Session-ID fields (`sessionIDPlacement`, `sessionIDKey`, `sessionIDTable`,
`sessionIDLength`) and the `scMin/MaxEachPostBytes` knobs are advanced; leave them
empty unless you're matching a specific upstream.

### Hysteria — `hysteriaSettings`

Only valid when the protocol is Hysteria2.

Field | Default | Meaning | 
`version` | `2` | Hysteria protocol version. | 
`auth` | (none) | Shared authentication string. | 
`udpIdleTimeout` | `60` | Seconds (2–600) before idle UDP sessions are dropped. | 
`masquerade` | — | Disguise as an HTTP/3 server: `type` `proxy`/`file`/`string` with `url`/`dir`/`content`, plus `headers` and `statusCode`. | 

## FinalMask — late-layer obfuscation

FinalMask wraps traffic after the transport and security layers, so it can
disguise transports that don't carry TLS (like mKCP) or add a second skin on top of
TLS. Masks are configured per direction:

- TCP masks — `fragment`, `sudoku`, `header-custom`, `xmc` (disguises the
stream as Minecraft protocol traffic; requires a password, with optional
hostname and player usernames).

- UDP masks — `salamander`, `mkcp-legacy`, `header-custom`, `xdns`, `xicmp`,
`noise`, `sudoku`, `realm`. (`mkcp-legacy` reproduces the old mKCP header
obfuscation.)

- QUIC params — congestion control (`reno`, `bbr`, `brutal`, `force-brutal`),
Brutal up/down rates, `udpHop` (rotate the QUIC port across a range to dodge
port blocking), and receive-window tuning.

FinalMask replaces the per-transport `header`/`seed` obfuscation that older Xray
builds exposed.

## sockopt — low-level socket options

`sockopt` rides alongside any transport and tunes the underlying socket. The most
useful fields:

Field | Default | Meaning | 
`tcpFastOpen` | `false` | Enable TCP Fast Open. | 
`tcpcongestion` | `bbr` | Congestion control: `bbr`, `cubic`, or `reno`. | 
`tproxy` | `off` | Transparent proxy mode: `off`, `redirect`, or `tproxy`. | 
`domainStrategy` | `AsIs` | How addresses resolve (`UseIP`, `ForceIPv4`, …). | 
`dialerProxy` | (none) | Chain this outbound's dialing through another outbound tag. | 
`interface` | (none) | Bind to a specific network interface. | 
`mark` | `0` | SO_MARK for policy routing (`0` = unset). | 

Numeric fields left at `0` are omitted on the wire so Xray keeps OS defaults.
Advanced entries (`happyEyeballs`, `customSockopt[]`, keepalive timers) are
available for special cases.

## Security

The security layer is one of `none`, `tls`, or `reality`, with these
eligibility rules:

Security | Eligible transports | Eligible protocols | 
TLS | `tcp`, `ws`, `grpc`, `httpupgrade`, `xhttp` | VLESS, VMess, Trojan, Shadowsocks (Hysteria2 is always TLS) | 
REALITY | `tcp`, `grpc`, `xhttp` | VLESS, Trojan | 

mKCP and Hysteria don't take a separate TLS/REALITY layer — mKCP runs plaintext
(obfuscate with FinalMask), and Hysteria is QUIC/TLS by design. REALITY disguises
your server as a real TLS site and needs no certificate — see
REALITY.

## XTLS-Vision flow

The `xtls-rprx-vision` flow is fast and DPI-resistant. It's available for
VLESS when either:

- the transport is raw TCP with TLS or REALITY security (classic
XTLS-Vision), or

- the transport is XHTTP with VLESS encryption enabled (see below).

Set the flow on the VLESS client, not the inbound. With classic Vision on
TCP, the panel can also offer a Vision seed once a client uses the flow.

## VLESS encryption (ML-KEM)

VLESS supports post-quantum encryption (ML-KEM / `mlkem768x25519`), stored in
the inbound's `decryption` (server) and clients' `encryption` (for link
generation). When enabled, it unlocks the Vision flow over XHTTP. Generate the
keys from the panel's VLESS settings.

## Shadowsocks ciphers

Shadowsocks inbounds support both classic ciphers and Shadowsocks-2022
(method names starting with `2022-blake3-`). Most ciphers are multi-user;
`2022-blake3-chacha20-poly1305` is single-user.

Transports and security must match on both ends. The client's share link
encodes them (`type=ws`, `security=reality`, `flow=xtls-rprx-vision`, …) —
decode any link with the share-link inspector.


=== SOURCE: https://docs.sanaei.dev/docs/config/tuic
# TUIC
Set up a TUIC inbound in 3x-ui — QUIC congestion control, 0-RTT handshakes, and multi-user authentication.

TUIC (v5) is a proxy protocol built directly on top of the QUIC (HTTP/3) transport
layer. It uses 0-RTT handshakes, connection multiplexing without head-of-line blocking,
and custom congestion control algorithms to maintain stable connections over lossy or
unstable networks.

TUIC runs as an in-process native Go server inside 3x-ui. Decrypted traffic is bridged into Xray-core via a loopback SOCKS5 tunnel, enabling full Xray routing rules, cascading outbounds (e.g. TUIC → VLESS / WARP), per-client traffic quotas (`totalGB`), and zero-downtime hot user updates without restarting the port.

## Key settings

### Server, QUIC & client-profile parameters

Field | Description | 
Port | UDP port for incoming client QUIC connections. | 
Certificate & Key | Full TLS certificate chain and private key. QUIC mandates TLS encryption; self-signed certificates or valid Let's Encrypt / ACME certs are supported. | 
SNI | Client-profile Server Name Indication. Set it to the domain covered by the server certificate; this field does not configure the listener certificate. | 
Congestion Control | QUIC congestion control algorithm used in the server setting and exported client profile: `bbr`, `cubic`, or `new_reno`. The server runs BBR or New Reno; when CUBIC is selected, the client profile keeps CUBIC while this server currently falls back to New Reno. | 
ALPN | Application-Layer Protocol Negotiation tokens (default: `h3`). | 
UDP Relay Mode | Client-profile packet mode: `native` (QUIC datagrams) or `quic` (unidirectional streams). The server accepts both modes regardless of this exported preference. | 
Zero-RTT Handshake | Enables 0-RTT connection resumption to eliminate initial handshake round-trips for returning clients. | 
Authentication Timeout | Maximum time (seconds) allowed for client authentication before disconnecting (default: `3s`). | 
Max Idle Time | Inactivity timeout (seconds) before closing idle QUIC connections (default: `15s`). | 
Max Packet Size | Maximum UDP relay packet size in bytes (default: `1500`). | 

## Set it up in the panel

### Add an inbound
Create a new inbound and choose protocol TUIC. Assign a UDP port (e.g. `8443` or `443`).

### Select TLS certificate
Provide the certificate file path and private key file path (or paste their contents). Make sure the configured SNI matches the certificate domain.

### Configure QUIC options
The panel fills recommended defaults (`bbr`, `h3`, `native` UDP relay). Adjust timeouts or enable Zero-RTT Handshake if desired.

### Add clients
Each client requires an Email identifier, a UUID (token), and a Password. The panel automatically generates secure random credentials when creating clients.

### Export and connect
Copy the client's share link (`tuic://…`) or open the QR modal to download a ready-to-use Clash / Mihomo YAML configuration.

## Client support & configuration

TUIC v5 is supported by modern proxy clients including Clash Verge Rev, Mihomo, Flclash, sing-box, and v2rayN.

### Clash / Mihomo configuration

The panel provides automatic YAML export for Clash/Mihomo in the client QR modal:

clash-tuic.yaml

`proxies:
 - name: "3x-ui-tuic"
 type: tuic
 server: vpn.example.com
 port: 8443
 uuid: 8a47f2b1-5e8c-4a3d-9b1e-7f6c5d4a3b2a
 password: secure-random-password
 alpn:
 - h3
 sni: vpn.example.com
 congestion-controller: bbr
 udp-relay-mode: native
 reduce-rtt: false
 skip-cert-verify: false`

### Share link format

TUIC share links use standard URI formatting:

`tuic://<uuid>:<password>@<host>:<port>?congestion_control=bbr&alpn=h3&sni=vpn.example.com&udp_relay_mode=native&allow_insecure=0#Remark`

## Architecture & Features

- Native in-process Go engine: TUIC v5 runs 100% natively in Go within the 3x-ui process. No external binaries or sidecars to download or maintain.

- Full Xray routing & cascading: Decrypted traffic passes directly through Xray's routing engine. Inbound tags (`in-<port>-udp`) work seamlessly with routing rules, domain/IP blocks, and cascading to any outbound proxy (VLESS, Shadowsocks, WARP, etc.).

- Per-client traffic limits & expiration: Individual traffic quotas (`totalGB`) and expiration timestamps (`expiryTime`) are tracked and enforced for each client.

- Live speed & traffic totals: Native TUIC client counters are sampled every 10 seconds and sent to the panel for per-client live speed. Xray meters inbound totals through the loopback relay; TUIC's client-speed event does not add inbound totals again.

- UDP resource bounds: Each QUIC connection can hold up to 256 active UDP associations. Idle associations are closed after five minutes. This is a per-connection limit, not a node-wide association cap. TUIC uses a reserved loopback SOCKS relay port in `64001–65000`; 3x-ui checks it against managed inbound and relay ports.

- Zero-downtime client updates: Adding, modifying, or disabling clients updates the in-memory user registry instantly without restarting the UDP port or interrupting existing client sessions.

- Deployment: A TUIC inbound can be created on, or cloned to, a sub-node. The node's own panel runs the TUIC server, so the node must run panel v3.8.0 or newer; the master refuses an older node.


=== SOURCE: https://docs.sanaei.dev/docs/guide/first-login
# First Login
Find your generated 3x-ui credentials, reach the panel, enable two-factor auth, and harden it before exposing anything.

After installation, your first job is to log in and secure the panel before
exposing anything else.

## Reach the panel

The panel is served at:

`http://<your-server-ip>:<port>/<web-base-path>`

The default port is 2053 and the default base path is `/` — but a script
install randomly generates the username, password, port, and web base
path, so check your actual values.

### Find your credentials

A script install prints a credential summary when it finishes and also writes it
to a root-only file:

/etc/x-ui/install-result.env (mode 600)

`XUI_USERNAME=...
XUI_PASSWORD=...
XUI_PANEL_PORT=...
XUI_WEB_BASE_PATH=...
XUI_ACCESS_URL=...
XUI_API_TOKEN=...
XUI_DB_TYPE=sqlite`

If you missed them, use the management tools:

`x-ui # menu → 11 (View Current Settings)
x-ui settings # or the one-shot form`

For Docker, read the generated credentials from the container logs, or run
`docker exec -it <container> x-ui setting -show`.

If your panel still uses the default `admin` / `admin` (the panel warns when it
does), change it immediately — before creating any inbounds.

## Change credentials, port, and path

A non-default port and a long, random web base path make the panel much
harder to find. Change them from Panel Settings in the UI, or from the
`x-ui` menu:

- 7 — Reset Username & Password (optionally disabling 2FA at the same time)

- 8 — Reset Web Base Path (randomizes it)

- 10 — Change Port

Changing your username or password logs out all existing sessions and, if
two-factor auth was on, disables it.

## Two-factor authentication (2FA)

3x-ui supports TOTP two-factor auth (compatible with Google Authenticator, Aegis,
etc.). Enable it in Panel Settings — once enabled, the login page asks for a
6-digit code in addition to your password, and turning it on forces everyone to
log in again. You can disable it from the menu's Reset Username & Password
step or with `x-ui setting -resetTwoFactor`.

## Built-in login protection

- Brute-force limiter: after 5 failed logins from the same IP/username
within 5 minutes, that combination is blocked for 15 minutes.

- Generic errors: the login page reports "wrong username or password" for
both bad credentials and bad 2FA codes, so it leaks nothing.

- Sessions last `sessionMaxAge` minutes (default 360 = 6 hours) and are
invalidated when you change credentials.

- LDAP can be enabled as an auth fallback in Panel Settings.

## Essential hardening checklist

### Set strong, unique credentials
Replace the generated (or `admin/admin`) username and password with strong values.

### Use a non-default port and random base path
Move the panel off `2053` and serve it under a long random path.

### Enable two-factor authentication
Turn on 2FA so a leaked password alone can't grant access.

### Put the panel behind TLS
Use a valid certificate (via the `x-ui` menu's SSL management, or a reverse
proxy) so the panel is only reachable over HTTPS.

### Restrict access with a firewall
Open only the ports you actually need, and consider limiting panel access by IP.

Want the panel on a clean domain with automatic HTTPS? See
Reverse proxy. For deeper hardening, see
Security.


=== SOURCE: https://docs.sanaei.dev/docs/guide
# Meet 3x-ui
A web panel for Xray-core — manage inbounds, protocols, clients, and subscriptions from your browser instead of editing JSON by hand.

3x-ui is a web control panel that sits on top of
Xray-core, the proxy engine that actually
moves your traffic. Instead of writing and reloading Xray's JSON configuration
by hand, you manage everything — inbounds, protocols, clients, certificates,
subscriptions — from a browser dashboard.

## How the pieces fit together

- The panel is the management layer: it stores your configuration in a
database, renders the dashboard, exposes a REST API, and writes the live Xray
configuration.

- Xray-core is the data plane: it terminates client connections on your
inbounds and forwards traffic to its destination.

- Client apps (such as v2rayNG, Clash/Mihomo, Hiddify, and others) connect
using a share link or a subscription that the panel generates for each client.

## What it gives you

- A dashboard for inbounds across every major protocol — VLESS, VMess,
Trojan, Shadowsocks, WireGuard, AmneziaWG, TUIC v5, Hysteria2, SOCKS, HTTP, and Dokodemo-door.

- First-class REALITY and XTLS-Vision support for stealthy, fast
transports.

- Per-client traffic quotas, expiry dates, IP limits, online status, and
one-click share links / QR codes.

- Subscriptions in VLESS, Clash/Mihomo, and JSON formats.

- Operational tooling: multi-node management, Telegram and Discord bots, backups,
Fail2ban-based IP limiting, and a documented REST API.

## Under the hood

Layer | Technology | 
Backend | Go with the Gin web framework | 
Frontend | TypeScript / React | 
Database | SQLite (default) or PostgreSQL | 
Proxy engine | Xray-core (bundled and managed by the panel) | 

The default SQLite database lives at `/etc/x-ui/x-ui.db`, and the panel listens
on port 2053 by default. Both are configurable — see
First login and the environment variable reference.

## Who it's for

3x-ui is aimed at anyone running their own Xray server: from a single personal
VPS to operators managing many nodes and clients. If you want the power of
Xray-core without living in JSON config files, this is for you.

3x-ui is an enhanced fork of the original X-UI project, adding broader protocol
support, improved stability, per-client traffic accounting, multi-node
management, and many quality-of-life features.

Ready to install? Continue to Installation.


=== SOURCE: https://docs.sanaei.dev/docs/guide/installation
# Installation
Install 3x-ui via the official script (stable, pinned, or dev-latest), unattended/cloud-init, or Docker — and choose SQLite or PostgreSQL.

3x-ui runs on a wide range of Linux distributions — Ubuntu, Debian, Armbian,
Fedora, CentOS, RHEL, AlmaLinux, Rocky Linux, Oracle Linux, Amazon Linux,
Virtuozzo, Arch, Manjaro, openSUSE (Tumbleweed/Leap), Alpine — and Windows,
across `amd64`, `386`, `arm64`, `armv7`, `armv6`, `armv5`, and `s390x`.

Run the script installer as root (or with `sudo`). It installs a service,
sets up the `x-ui` management command, and enables the panel on boot.

The official script is the recommended path. During installation it generates a
random username, password, and access (web base) path, sets up the service,
and installs the `x-ui` management command.

latest stable

`bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)`
Install a specific version by appending its tag:

pinned version

`bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh) v3.4.0`
Install the rolling dev build (the latest per-commit pre-release from `main`
— not a stable release) by passing `dev-latest`:

rolling dev build

`bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh) dev-latest`
When it finishes, note the printed login details and run `x-ui` to open the
management menu, then
continue to First login.

## Build your install command

Tailor the command to your setup:

### 

Methodscriptdocker
Versionblank = latest stable · a tag like v3.4.0 · or dev-latest for the rolling dev build
Enable Fail2ban

Run on your server
`bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)`

## Choose a database

You pick the storage backend at install time:

- SQLite (default) — a single file at `/etc/x-ui/x-ui.db`. Zero setup.

- PostgreSQL — for high client counts or multi-node setups. The installer
can install it locally or use a DSN you provide.

See Database for details and SQLite→PostgreSQL
migration.

## Unattended / cloud-init

The installer also runs non-interactively for automation. Set
`XUI_NONINTERACTIVE=1` (or run with no TTY) and it installs end-to-end with zero
prompts, generating random credentials and writing them to
`/etc/x-ui/install-result.env`:

`XUI_NONINTERACTIVE=1 bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)`

The repo's `deploy/`
directory has ready-made cloud-init user-data for unattended installs on any
cloud (Hetzner, AWS, DigitalOcean, Vultr, GCP, Azure, Oracle).

## Next steps

### First login
Reach the panel and secure it.

### Update & uninstall
The x-ui menu, updates, and removal.

### REALITY
Configure your first stealthy inbound.


=== SOURCE: https://docs.sanaei.dev/docs/guide/update-uninstall
# Update & Uninstall
Manage 3x-ui with the x-ui menu and CLI — update (stable, dev, or legacy), change settings, and uninstall cleanly.

After a script install, the `x-ui` command is your control center. Run it with
no arguments for the interactive menu, or pass a subcommand for a one-shot action.

`x-ui`

## The `x-ui` management menu

The menu (items `0`–`28`) shows the panel/Xray status at the top, then:

# | Item | What it does | 
1 | Install | (Re)install from the remote script | 
2 | Update | Update to the latest stable release | 
3 | Update to Dev Channel (latest commit) | Update to the rolling `dev-latest` build | 
4 | Update Menu | Update just the `x-ui` menu script | 
5 | Legacy Version | Install a specific older version (prompts for a tag) | 
6 | Uninstall | Remove 3x-ui (see below) | 
7 | Reset Username & Password | Set new credentials; optionally disable 2FA | 
8 | Reset Web Base Path | Randomize the web base path | 
9 | Reset Settings | Reset panel settings (your account is preserved) | 
10 | Change Port | Change the panel port | 
11 | View Current Settings | Show username, port, web base path, cert paths | 
12–14 | Start / Stop / Restart | Control the panel service | 
15 | Restart Xray | Reload only Xray-core | 
16 | Check Status | Service status | 
17 | Logs Management | View debug logs / clear logs | 
18–19 | Enable / Disable Autostart | Toggle start-on-boot | 
20 | SSL Certificate Management | Let's Encrypt (domain or IP), custom paths, renew/revoke | 
21 | Cloudflare SSL Certificate | DNS-01 wildcard cert via Cloudflare | 
22 | IP Limit Management | Fail2ban-based per-client IP limits | 
23 | Firewall Management | `ufw` install and port rules | 
24 | SSH Port Forwarding Management | Bind the panel to localhost and tunnel over SSH | 
25 | PostgreSQL Management | Install/migrate/manage PostgreSQL | 
26 | Enable BBR | Toggle the BBR congestion-control sysctl | 
27 | Update Geo Files | Update geoip/geosite data (Loyalsoldier, IR, RU) | 
28 | Speedtest by Ookla | Run an Ookla speed test | 
0 | Exit | — | 

Some of these have their own pages: SSL certificates
(items 20–21), Security (IP limits, firewall),
Reverse proxy and Panel settings
(TLS), and Database (PostgreSQL).

## CLI subcommands

For scripts and quick actions, `x-ui` also takes a subcommand directly:

Command | Action | 
`x-ui start` / `stop` / `restart` | Control the service | 
`x-ui restart-xray` | Reload only Xray-core | 
`x-ui status` | Show status | 
`x-ui settings` | Show current settings | 
`x-ui enable` / `disable` | Toggle autostart on boot | 
`x-ui log` | Tail the debug log | 
`x-ui banlog` | Show Fail2ban ban log | 
`x-ui update` | Update to the latest stable release | 
`x-ui update-dev` | Update to the rolling `dev-latest` build | 
`x-ui legacy` | Install a specific older version (prompts) | 
`x-ui update-all-geofiles` | Update all geo files, restart if changed | 
`x-ui migrate-db --dsn …` | Migrate SQLite → PostgreSQL (see Database) | 
`x-ui install` / `uninstall` | Install / uninstall | 

## Updating

- Stable: menu option 2 or `x-ui update`. Re-running the install script
also updates in place.

- Dev channel: menu option 3 or `x-ui update-dev` — the rolling
`dev-latest` per-commit build (not a stable release).

- A specific older version: menu option 5 (Legacy Version).

Updating preserves your database and settings. Take a
backup before a major-version jump.

Docker users update differently — pull the new image and recreate the
container (`docker compose pull && docker compose up -d`) rather than using the
`x-ui` update commands.

## Uninstalling

Menu option 6 or `x-ui uninstall`. It stops and disables the service, removes
the service unit, and deletes `/etc/x-ui/` and the install folder. If the panel
used a locally-installed PostgreSQL, it offers to purge that too (a separate,
irreversible confirmation).

Uninstalling removes the database (`/etc/x-ui/x-ui.db`) and your configuration.
Back up first if you might need it.


=== SOURCE: https://docs.sanaei.dev/docs/help/faq
# FAQ
Frequently asked questions about 3x-ui — licensing, supported systems, databases, and clients.

## Is 3x-ui free and open source?

Yes. 3x-ui is open source under the GPL-3.0 license. The source is on
GitHub.

## What systems does it run on?

Most major Linux distributions (Ubuntu, Debian, CentOS/RHEL and derivatives,
Fedora, Arch, Alpine, and more) across `amd64`, `arm64`, and other architectures.
It also runs as a Docker container. See Installation.

## SQLite or PostgreSQL?

SQLite is the default and is fine for most deployments. PostgreSQL is available
for larger setups via `XUI_DB_TYPE=postgres` and `XUI_DB_DSN` — see the
environment variables.

## Which client apps work with it?

Any Xray-compatible client — for example v2rayNG, Hiddify, and Clash/Mihomo.
Import a client's share link or QR code, or use a
subscription.

## How is 3x-ui different from x-ui?

3x-ui is an enhanced fork of the original X-UI project. It adds broader protocol
support, improved stability, per-client traffic accounting, multi-node
management, a 13-language UI, and many quality-of-life features.

## How do I update?

Re-run the install script (it updates in place), or pull the new Docker image.
See Installation and the
releases page.

## Where can I get help?

Join the official Telegram channel @XrayUI for
announcements and community support, or open an issue on
GitHub. For common problems, start
with Troubleshooting.


=== SOURCE: https://docs.sanaei.dev/docs/help/migration
# Migration
Migrate to 3x-ui from x-ui, between servers, or between 3x-ui versions.

## Between servers

Moving to a new server is a database move:

### Back up the old server
Copy the database (default `/etc/x-ui/x-ui.db`) and your certificates. See
Backup & restore.

### Install 3x-ui on the new server
Use the same install method and a compatible version. See
Installation.

### Restore the database
Stop the panel, put the database in place, restore certificates, and start the
panel. Update any IP/domain-specific settings.

## Between 3x-ui versions

Within the same backend, upgrading is usually just re-running the installer or
pulling a new image — the panel migrates its own database. Across major
versions, read the release notes
first and take a backup.

## From x-ui

Importing an older x-ui panel's database directly into 3x-ui is not
supported — the schemas differ. Install 3x-ui fresh and recreate
inbounds/clients, exporting share links from the old panel as you go.

Always take a backup before any migration, and keep the old server running
until you've verified the new one.


=== SOURCE: https://docs.sanaei.dev/docs/help/troubleshooting
# Troubleshooting
Fix common 3x-ui problems — the panel won't start, 502 errors, certificate issues, and clients that can't connect.

A checklist for the most common issues. When in doubt, raise the log level
(`XUI_LOG_LEVEL=debug`) and check the panel and Xray logs.

## The panel won't start

- Check the service status and logs (`x-ui` menu → status/logs).

- Make sure the panel port isn't already in use by another service.

- Verify the database path is writable (default `/etc/x-ui/x-ui.db`).

## 502 / panel unreachable behind a proxy

- Confirm the panel is actually listening on the upstream port (e.g. `2053`).

- Ensure your reverse proxy passes WebSocket
upgrade headers and points at the correct port and web base path.

- Check the firewall isn't blocking the proxy → panel connection.

## Certificate problems

- The domain's DNS must point at the server before issuing a certificate.

- Ports 80/443 must be reachable for HTTP/TLS validation (or use DNS validation).

- For REALITY, remember it needs no certificate — the issue is usually a bad
`dest`/SNI instead (see REALITY pitfalls).

## A client can't connect

- Decode the client's link with the
share-link inspector and confirm every parameter.

- Check the transport and security match on both ends.

- Make sure the client hasn't hit its traffic, expiry, or IP limit.

- Confirm the inbound port is open in the firewall.

Still stuck? Search the
GitHub issues — your symptom has
probably been seen before.


=== SOURCE: https://docs.sanaei.dev/docs
# 3x-ui Documentation
Official documentation for 3x-ui — an advanced web panel for managing Xray-core servers, proxies, clients, and subscriptions.

3x-ui is an open-source web panel for deploying and managing
Xray-core servers. It gives you a modern
dashboard for inbounds, protocols, clients, traffic accounting, subscriptions,
and more — without hand-editing Xray JSON on the command line.

This site is the official documentation and a set of interactive, in-browser
tools (config generators) that run entirely on your device — no data ever
leaves the page.

## Start here

### What is 3x-ui?
The big picture: Xray-core, the panel, and who it's for.

### Installation
Install via script, Docker, or manually.

### First login
Reach the panel and harden it before anything else.

### REALITY
Set up VLESS + REALITY with XTLS-Vision.

## Highlights

- Every major protocol — VLESS, VMess, Trojan, Shadowsocks, WireGuard,
AmneziaWG, TUIC v5, Hysteria2, SOCKS, HTTP, and Dokodemo-door.

- REALITY & XTLS-Vision — modern, censorship-resistant transports.

- Per-client controls — traffic quotas, expiry dates, IP limits, share
links, and QR codes.

- Subscriptions — VLESS, Clash/Mihomo, and JSON formats.

- Operations — multi-node management, Telegram and Discord bots, backups, and a REST API.

New to Xray? Read What is 3x-ui? first — it explains how the panel, Xray-core, and
your client apps fit together.


=== SOURCE: https://docs.sanaei.dev/docs/operations/backup-restore
# Backup & Restore
Back up and restore your 3x-ui database and certificates, manually or via the Telegram bot.

Your entire configuration — inbounds, clients, settings — lives in the panel's
database. Back it up regularly so you can recover or migrate.

## What to back up

- The database — SQLite at `/etc/x-ui/x-ui.db` by default (or your
PostgreSQL database if you use that backend).

- Certificates — anything under `/root/cert/` (or wherever you store TLS
certs).

## Manual backup

You can download a backup from the panel's overview, or copy the database file
directly from the server:

copy the SQLite database

`cp /etc/x-ui/x-ui.db /root/x-ui-backup-$(date +%F).db`

To restore, stop the panel, put the database back in place, and start it again.

Restore a backup onto the same major version it came from when possible.
Across major upgrades, let the panel run its migrations rather than forcing an
old schema.

## Automated bot backups (Telegram & Discord)

If you've configured the Telegram bot or Discord bot, enable `tgBotBackup` or `discordBotBackup` to attach a backup to the periodic report (on the `tgRunTime` / `discordRunTime` schedule, default daily). The bot sends both the database and the Xray `config.json` directly to your admin chat or channel, ensuring an off-server copy. Admins can also request a backup on demand from the Telegram bot's menu or using `!backup` in Discord.

## SQLite dump / restore

The `x-ui migrate-db` command converts the SQLite database to and from a plain
SQL text dump (handy for inspection or transferring between machines):

`x-ui migrate-db --dump /root/x-ui.sql # SQLite -> SQL text
x-ui migrate-db --restore /root/x-ui.sql # SQL text -> SQLite`

To move to PostgreSQL instead, see Database.

Whatever method you use, store backups off the server and test a restore
occasionally — an untested backup isn't a backup.


=== SOURCE: https://docs.sanaei.dev/docs/operations/multi-node
# Multi-node & Managed Hosts
Manage multiple 3x-ui panels from one master, with API-token or mTLS trust, heartbeats, and per-inbound host overrides for subscriptions.

3x-ui can manage multiple servers from a single master panel, and override
how each inbound is advertised in subscriptions with managed hosts.

## Nodes

A node is another 3x-ui panel that your master panel manages over the node's
API. The master polls each node and shows its status, versions, CPU/memory,
uptime, and traffic in one place.

### Add a node

Provide the node's connection details:

Field | Notes | 
Name | Unique label (e.g. `de-fra-1`). | 
Scheme | `https` (default) or `http`. | 
Address / Port | The node panel's host and port. | 
Base path | The node's web base path. | 
API token | A Bearer token created on the node (not needed in mTLS mode). | 
TLS verify | `verify` (default), `skip`, `pin` (pin a cert SHA-256), or `mtls`. | 
Inbound sync | `all` inbounds, or `selected` by tag. | 
Outbound tag | Optionally reach the node through a named outbound (egress bridge). | 

The master verifies reachability when you add or test a node. It then sends a
heartbeat every few seconds, updating the node's status (`online` / `offline`)
and emitting `node.up` / `node.down` events (see the
Telegram bot and Discord bot).

Nodes are identified by a stable per-panel GUID, so a node keeps its identity
across restarts. A node can itself manage further nodes — the master surfaces
those as read-only transitive sub-nodes (Node 1 → Node 2 → Node 3).

### Mutual TLS (mTLS) between master and node

For the strongest trust, use `tlsVerifyMode = mtls` (requires `https`):

### Get the master's CA
On the master, fetch its node-auth CA certificate (the CA private key never
leaves the panel).

### Trust it on the node
Paste that CA into the node's "trusted CA" setting. It takes effect on the node's
next restart.

### Switch the node to mTLS
Set the node's TLS verify mode to `mtls`. The master now presents a client
certificate instead of an API token.

## Managed hosts

A managed host is an override endpoint attached to an inbound. At
subscription time, each enabled host renders an additional share link / proxy
with its own address, port, TLS, SNI, host header, path, and more — superseding
the older "external proxy" list. Use them to:

- front an inbound through a CDN (Cloudflare) with a different address/SNI,

- advertise multiple domains or per-region endpoints for one inbound,

- tweak ALPN, fingerprint, ECH, or mux per endpoint.

Each host has a remark (which supports the same
template variables), an
enable toggle, a sort order, and can be excluded from specific subscription
formats or scoped to specific nodes.

Hosts whose address/port point at a CDN let you keep the real server address
private while clients connect through the CDN edge.

## Related

### Outbounds & routing
WARP, NordVPN, outbound subscriptions, and routing.

### Subscription
How hosts shape subscription output.


=== SOURCE: https://docs.sanaei.dev/docs/operations/outbounds-routing
# Outbounds & Routing
Shape egress in 3x-ui — WARP, NordVPN, PIA WireGuard, outbound subscriptions, routing rules, and load balancers.

Inbounds accept clients; outbounds decide where their traffic goes next.
3x-ui can route traffic through Cloudflare WARP, NordVPN, Private Internet Access
(WireGuard), or arbitrary outbound pools imported from a subscription,
and select between them with routing rules and balancers.

## Editing outbounds & routing

Outbounds, routing rules, balancers, DNS, and logging all live in the Xray
configuration (the config template you edit under Xray Settings). There's no
separate per-rule UI — you edit the JSON, and the panel reloads Xray. The panel
also offers an outbound connectivity test and a route test (ask the
running core which outbound a given destination would use).

## Build an outbound

Every outbound is a JSON object with up to four parts: a `tag` (referenced by
routing rules and balancers), a `protocol`, protocol-specific `settings`,
and — for proxy protocols — `streamSettings` that must match the remote
inbound's transport and security. Two outbounds are almost always present:

- `freedom` sends traffic straight to its destination — the default egress.
Optionally set a `domainStrategy` (e.g. `UseIP`) to control how hostnames resolve.

- `blackhole` drops traffic. Route unwanted destinations (ads, torrents) here.

freedom + blackhole

`{
 "outbounds": [
 { "tag": "direct", "protocol": "freedom", "settings": {} },
 { "tag": "block", "protocol": "blackhole", "settings": {} }
 ]
}`

A proxy outbound (VLESS, VMess, Trojan, Shadowsocks) forwards to another
server — handy for chaining or sending select traffic abroad. Mind the wire
shapes 3x-ui uses: VLESS is the flat form (`address`/`port`/`id`/`flow`/
`encryption`), VMess uses `settings.vnext[]`, and Trojan/Shadowsocks use
`settings.servers[]`. The `streamSettings` must mirror the destination's
transport and security.

Assemble any outbound below and paste the JSON into Xray Settings → Outbounds:

### 

Kindfreedomblackholevlessvmesstrojanshadowsockssockshttpwireguardwarp
Tag
Address
Port
UUID (id)
Flow

Transporttcpkcpwsgrpchttpupgradexhttp
Securitynonetlsreality
SNI (serverName)
Fingerprintchromefirefoxsafariiosandroidedgerandom
Public key (pbk)
Short ID (sid)

Outbound (Xray JSON)
`{
 "tag": "proxy",
 "protocol": "vless",
 "settings": {
 "address": "example.com",
 "port": 443,
 "id": "",
 "flow": "",
 "encryption": "none"
 },
 "streamSettings": {
 "network": "tcp",
 "security": "reality",
 "tcpSettings": {
 "header": {
 "type": "none"
 }
 },
 "realitySettings": {
 "fingerprint": "chrome",
 "serverName": "www.microsoft.com"
 }
 }
}`

## Cloudflare WARP

WARP lets your server egress through Cloudflare's network. 3x-ui can register a
WARP account for you and wire it into a WireGuard outbound tagged `warp`:

### Add a `warp`-tagged outbound
Create a WireGuard outbound with the tag `warp` in your Xray config.

### Register WARP
From the panel's WARP controls, register an account. 3x-ui fills the outbound's
keys, addresses, reserved bytes, and peer endpoint automatically.

### (Optional) auto-rotate the IP
Set a WARP update interval (in days) to periodically rotate the WARP IP. A
free license can also be applied.

Route the traffic you want (for example specific domains) to the `warp` outbound
with a routing rule.

## NordVPN

3x-ui can fetch NordVPN (NordLynx/WireGuard) credentials from an access token (or
accept a private key directly) and list countries/servers, so you can build a
NordVPN outbound. Open Xray → Outbounds → More → NordVPN, sign in or save a
private key, select a server, and add the outbound. You can add several servers;
each hostname has a unique `nord-<hostname>` tag and cannot be added twice.

Reset on an added row keeps its server, tag, peer, and routing references but
refreshes its embedded private key from the currently stored NordVPN credentials.
Logout clears only those stored credentials. Existing outbounds continue to use
their embedded keys; remove unused NordVPN outbounds from the Outbounds list.

## PIA WireGuard

3x-ui can sign in with a PIA username and password, list countries/regions/servers
from the signed PIA server list, and build a WireGuard outbound. Open
Xray → Outbounds → More → PIA, sign in, pick a server, and add the outbound.
You can add several servers (one outbound per hostname). The tag is
`pia-<region>-<server>` (for example `pia-us-east-useast1`). Adding or using
Reset on a row registers a WireGuard key with PIA `/addKey` for that server.
The same hostname cannot be added twice. Logout clears the stored token only;
delete unused PIA outbounds from the Outbounds list. Reset and delete do not
revoke the WireGuard peer on the PIA account.

The password is not stored. The PIA API token is stored with the same
`NODE_TOKEN_ENCRYPTION` setting as node API tokens. If you retire an old
`XUI_NODE_TOKEN_KEY` without signing into PIA again, Add/Reset fail until you
re-login. Peer `allowedIPs` is IPv4-only (`0.0.0.0/0`).

## Outbound subscriptions (server pools)

An outbound subscription imports a remote share-link subscription and injects
its servers as outbounds into the running Xray config — without touching your
saved template. This is the recommended way to subscribe to a pool of servers.

Field | Default | Meaning | 
`url` | — | The remote subscription URL (SSRF-guarded). | 
`tagPrefix` | auto | Prefix for generated outbound tags (e.g. `hk-`); blank = `subN-`. | 
`updateInterval` | `600` | Refresh interval in seconds. | 
`prepend` | `false` | Place these outbounds before your manual ones. | 
`priority` | `0` | Merge order (lower first). | 

Imported outbounds get stable tags: the same server keeps the same tag across
refreshes, so exact-tag routing/balancer selectors stay pinned — while
prefix/wildcard selectors (e.g. `hk-*`) automatically pick up new servers as the
pool changes. Supported link schemes: `vmess`, `vless`, `trojan`, `ss`,
`hysteria2` (`hy2`), and `wireguard` (`wg`). The panel refreshes enabled
subscriptions on a timer and reloads Xray when something changes.

## Routing rules

Routing rules decide which outbound (or balancer) each connection uses. Each
rule is a `field`-type matcher: set any of `domain`, `ip`, `port`, `network`,
`protocol`, `inboundTag`, `sourceIP`, … and point it at an `outboundTag` or a
`balancerTag`. Rules are evaluated top-to-bottom — the first match wins, so
put specific rules above general ones.

route ads to blackhole, private IPs direct

`{
 "routing": {
 "domainStrategy": "IPIfNonMatch",
 "rules": [
 { "type": "field", "domain": ["geosite:category-ads-all"], "outboundTag": "block" },
 { "type": "field", "ip": ["geoip:private"], "outboundTag": "direct" }
 ]
 }
}`

## Balancers

A balancer groups outbounds by a selector (tag prefixes, including the
wildcard pools from outbound subscriptions) and spreads or fails traffic over them
with a strategy:

Strategy | Picks… | Needs a monitor | 
`random` | a random member per connection | no | 
`roundRobin` | members in rotation | no | 
`leastPing` | the lowest-latency member | `observatory` | 
`leastLoad` | the most stable member by sampled load | `burstObservatory` | 

Reference a balancer from a rule via `balancerTag`. `leastPing` and `leastLoad`
need a health monitor, which Xray places at the top level of the config
(`observatory` / `burstObservatory`, not inside `routing`). The panel can
report balancer status and override a balancer to a specific outbound for
testing.

Build the routing block — rules, balancers, and the matching observatory — here:

### 

Domain strategyAsIsIPIfNonMatchIPOnDemand

#### Balancers

Tag
Selector (comma-separated prefixes)
StrategyrandomroundRobinleastPingleastLoad
Fallback tag

#### Rules

Domain (comma)
IP (comma)
Port
Networkanytcpudptcp,udp
Inbound tag (comma)
Target kindoutboundbalancer
Target tag

Domain (comma)
IP (comma)
Port
Networkanytcpudptcp,udp
Inbound tag (comma)
Target kindoutboundbalancer
Target tag

Routing block (Xray JSON)
`{
 "routing": {
 "domainStrategy": "IPIfNonMatch",
 "rules": [
 {
 "type": "field",
 "domain": [
 "geosite:category-ads-all"
 ],
 "outboundTag": "block"
 },
 {
 "type": "field",
 "ip": [
 "geoip:private"
 ],
 "outboundTag": "direct"
 }
 ],
 "balancers": [
 {
 "tag": "balancer",
 "selector": [
 "proxy"
 ],
 "strategy": {
 "type": "leastPing"
 }
 }
 ]
 },
 "observatory": {
 "subjectSelector": [
 "proxy"
 ],
 "probeURL": "https://www.google.com/generate_204",
 "probeInterval": "1m",
 "enableConcurrency": true
 }
}`

Outbounds that reach external services are fetched with SSRF protection — by
default private/internal addresses are blocked unless you explicitly allow them
per source.


=== SOURCE: https://docs.sanaei.dev/docs/operations/reverse-proxy
# Reverse Proxy
Put the 3x-ui panel and subscription behind Nginx or Caddy with Let's Encrypt TLS.

A reverse proxy lets you serve the panel and subscription on a clean domain with
automatic HTTPS, and hide the real ports behind ports 80/443. Prefer to let the
panel terminate TLS directly? Get a certificate with the
`x-ui` SSL menu instead.

## Generate a config

### 

Servernginxcaddy
Domain
Panel port
Panel web base path
Certificate toolcertbotacme.sh

nginx server block
`server {
 listen 443 ssl http2;
 server_name panel.example.com;

 ssl_certificate /etc/letsencrypt/live/panel.example.com/fullchain.pem;
 ssl_certificate_key /etc/letsencrypt/live/panel.example.com/privkey.pem;

 location /panel/ {
 proxy_pass http://127.0.0.1:2053;
 proxy_http_version 1.1;
 proxy_set_header Upgrade $http_upgrade;
 proxy_set_header Connection "upgrade";
 proxy_set_header Host $host;
 proxy_set_header X-Real-IP $remote_addr;
 proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
 proxy_set_header X-Forwarded-Proto $scheme;
 proxy_read_timeout 3600s;
 proxy_send_timeout 3600s;
 }
}`

Obtain a certificate
`certbot certonly --nginx -d panel.example.com`

The panel uses WebSockets for live updates, so the proxy must pass the
`Upgrade`/`Connection` headers (the Nginx output above already does). Caddy
handles WebSocket upgrades automatically.

## Nginx + certificate

With Nginx, obtain a certificate with `certbot` (or `acme.sh`) and reference it
in the server block:

certbot

`certbot certonly --nginx -d panel.example.com`

Reload Nginx after installing the certificate, and set up automatic renewal
(`certbot renew` runs on a timer by default).

## Caddy

Caddy obtains and renews certificates for you — point a Caddyfile at the panel
and it just works:

Caddyfile

`panel.example.com {
 reverse_proxy 127.0.0.1:2053
}`

## Tips

- Keep the panel's web base path even behind a proxy; defense in depth.

- If you terminate TLS at the proxy, you may want `XUI_SKIP_HSTS=true` on the
panel — see the environment variables reference.

- Proxy the subscription server too, so its contents
are served over HTTPS.


=== SOURCE: https://docs.sanaei.dev/docs/operations/security
# Security
Harden 3x-ui — panel auth and 2FA, Fail2ban IP limits, firewall rules, BBR, and staying current.

A proxy panel is a high-value target. A few layers of hardening go a long way.

## Panel hardening

- Strong, unique credentials and two-factor auth (TOTP).

- A non-default panel port and a long, random web base path.

- TLS on the panel (directly or via a reverse proxy).

- The built-in login limiter blocks an IP/username after 5 failed attempts
in 5 minutes (for 15 minutes), and the panel can route its own egress through
an outbound.

See First login for the full checklist.

## Fail2ban & IP limits

Set an IP limit per client (see Clients) to cap the
number of simultaneous source IPs. Enforcement is handled by Fail2ban, which
3x-ui installs and configures for you (enabled by default on script installs, and
on Docker via `XUI_ENABLE_FAIL2BAN=true`).

Manage it from the `x-ui` menu (22 — IP Limit Management): install/configure,
change the ban duration (default 30 minutes), ban/unban an IP, view ban logs,
and check status. Under the hood:

- The jail is named `3x-ipl`; ban logs live at `/var/log/x-ui/3xipl.log` and
`/var/log/x-ui/3xipl-banned.log` (also via `x-ui banlog`).

- Bans cover all TCP/UDP except your SSH and panel ports, so a ban can't lock
you out of the server or panel.

On Docker, Fail2ban bans with `iptables`, which needs the `NET_ADMIN` (and
`NET_RAW`) capability — `docker-compose.yml` grants them. With a bare
`docker run`, add `--cap-add=NET_ADMIN --cap-add=NET_RAW` or bans are logged
but never applied.

## Firewall

Open only the ports you actually use: SSH, the panel port, the subscription
port, and your inbound ports. The `x-ui` menu (23 — Firewall Management) wraps
`ufw`, or generate rules here:

### 

Allow SSH (port 22)panel — 2053/tcpsubscription — 2096/tcpinbound (HTTPS) — 443/tcpinbound (UDP) — 443/udp

ufw
`ufw allow 22/tcp # SSH
ufw allow 2053/tcp # panel
ufw allow 443/tcp # inbound (HTTPS)
ufw enable`

nftables (/etc/nftables.conf)
`#!/usr/sbin/nft -f

flush ruleset

table inet filter {
 chain input {
 type filter hook input priority 0; policy drop;

 iif "lo" accept
 ct state established,related accept
 icmp type echo-request accept
 tcp dport 22 accept # SSH
 tcp dport 2053 accept # panel
 tcp dport 443 accept # inbound (HTTPS)
 }

 chain forward {
 type filter hook forward priority 0; policy drop;
 }

 chain output {
 type filter hook output priority 0; policy accept;
 }
}`

Make sure SSH stays allowed before enabling a default-deny firewall, or you can
lock yourself out. Test with a second session open.

## Network tuning (BBR)

The `x-ui` menu (26 — Enable BBR) toggles Google's BBR congestion control
(`net.ipv4.tcp_congestion_control = bbr`, `net.core.default_qdisc = fq`), which
often improves throughput on congested links.

## Keep current

Update 3x-ui and Xray-core regularly — security fixes land in new releases. Watch
the releases page and see
Update & uninstall.


=== SOURCE: https://docs.sanaei.dev/docs/operations/telegram-bot
# Telegram Bot
Connect a Telegram bot to 3x-ui for commands, periodic reports, event alerts (login, CPU, node up/down), backups, and client self-service.

3x-ui can drive a Telegram bot for monitoring, alerts, backups, and remote
management. Admins get full control; regular users (linked by Telegram ID) can
check their own usage and links.

Looking for news and community support? Join the official Telegram channel
@XrayUI. That's separate from the bot below, which you
run yourself to manage your own panel.

## Set it up

### Create a bot
Message @BotFather, send `/newbot`, and copy the bot
token.

### Find your Telegram ID
Get your numeric Telegram user ID (the bot's own `/id` command reports it once
connected). This is your admin ID.

### Configure the panel
In Panel Settings, enable the Telegram bot and set the token and admin chat
ID(s) (comma-separated). Save, then message your bot.

Validate your token, admin IDs, and report schedule before pasting them into the
panel:

### 

Bot token (from @BotFather)

Admin chat IDs (comma-separated)

Report schedule (tgRunTime)
Valid (macro)

Panel settings
`tgBotEnable = true
tgBotToken = <token>
tgBotChatId = <admin ids>
tgRunTime = @daily`

Bot API base (keep secret)
`https://api.telegram.org/bot<token>`

## Commands

These appear in the Telegram command menu: `/start`, `/help`, `/status`, `/id`.
Additional commands:

Command | Who | Action | 
`/start` | anyone | Greeting and the menu of inline buttons; an unlinked account gets only its Telegram ID | 
`/help` | both | The menu of inline buttons | 
`/status` | both | Confirm the bot is alive | 
`/id` | anyone | Show your Telegram numeric ID | 
`/usage <arg>` | both | Admins search clients; users look up their own usage | 
`/inbound <remark>` | admin | Show an inbound's details | 
`/restart` | admin | Restart Xray | 

A user is a Telegram account linked to at least one client. Any other account
can run only `/start` and `/id`; the bot ignores its other commands and
button taps. To link a customer, tap Invite Link on the client's card in the bot and
send them the `t.me` link: the first account to open it is linked to every
client that shares that Subscription ID. The Subscription ID is the invite code,
so keep it long and random. Each account gets five claim attempts an hour, and
admins are notified when one runs out.

Admins also get inline-button flows for server usage, sorted traffic reports,
resetting traffic, DB backups, ban logs, listing inbounds/clients, online
clients, "depleting soon", and a full add-client wizard. Regular users get
buttons for their own usage, subscription links, individual links, and QR codes.

## Reports & alerts

- 

Periodic report — on the `tgRunTime` schedule (default `@daily`), the bot
sends admins server usage (host, versions, uptime, load, memory, online
clients, traffic), a list of exhausted/expiring clients, and — if
`tgBotBackup` is on — a database + Xray config backup. Clients linked by
Telegram ID get their own expiry/quota warnings.

- 

Event alerts — selected by `tgEnabledEvents` (default `login.attempt,cpu.high`):

Event | When | 
`login.attempt` | A panel login succeeds or fails (with IP and username) | 
`cpu.high` | CPU exceeds `tgCpu` percent (default 80) | 
`memory.high` | Memory exceeds `tgMemory` percent (default 80) | 
`xray.crash` | Xray-core crashes | 
`outbound.down` / `outbound.up` | An outbound goes down / recovers | 
`node.down` / `node.up` | A node goes offline / comes back | 

The warning lead times come from `expireDiff` (days before expiry) and
`trafficDiff` (GB of quota remaining); both default to `0` (off).

## Settings

Setting | Default | Meaning | 
`tgBotEnable` | `false` | Master on/off. | 
`tgBotToken` | (secret) | Bot API token. | 
`tgBotChatId` | (none) | Comma-separated admin Telegram IDs. | 
`tgBotProxy` | (none) | `socks5://`, `http://`, or `https://` proxy. | 
`tgBotAPIServer` | (default) | Custom Telegram Bot API server. | 
`tgRunTime` | `@daily` | Report schedule (cron / `@daily` / `@every …`). | 
`tgBotBackup` | `false` | Attach a DB backup to the periodic report. | 
`tgCpu` / `tgMemory` | `80` / `80` | CPU / memory alert thresholds (percent). | 
`tgLang` | `en-US` | Bot language. | 
`tgEnabledEvents` | `login.attempt,cpu.high` | Which events to deliver. | 

The bot token controls your bot — keep it secret and only add trusted admin
chat IDs. Login alerts never include passwords.

Email (SMTP) notifications mirror the same events (`smtpEnabledEvents`) if you'd
rather receive alerts by email — configure SMTP in Panel Settings.


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/api-tokens
# API Tokens
Manage scoped Bearer tokens for programmatic auth. Tokens grant admin, monitor, or node-sync access, may expire, and are stored as SHA-256 hashes. The plaintext is returned only once at creation.

## List every API token, enabled or not. The token value is never returned — only metadata.
GET
/panel/api/setting/apiTokens

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/setting/apiTokens"`

`{ "success": true, "obj": [ { "id": 1, "name": "default", "enabled": true, "createdAt": 1736000000 } ]}`

## Mint a scoped API token. The server-generated plaintext is returned only once and stored as a hash.
POST
/panel/api/setting/apiTokens/create

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`name*`string

Human-readable label, e.g. "central-panel-a".

`scope?`string

admin (default), monitor, or node-sync.

`expiresAt?`integer

Future Unix milliseconds, or 0 for no expiry.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X POST "https://example.com/panel/api/setting/apiTokens/create" \ -H "Content-Type: application/json" \ -d '{ "name": "central-panel-a", "scope": "node-sync", "expiresAt": 1798761600000 }'`

`{ "success": true, "obj": { "createdAt": 1736000000, "enabled": true, "expiresAt": 0, "id": 2, "name": "central-panel-a", "scope": "admin", "token": "new-token-string" }}`

## Permanently delete a token. Any caller using it stops authenticating immediately.
POST
/panel/api/setting/apiTokens/delete/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Token row ID.

### Request Body

`application/json`

- body

- body
- …

`expectedScope*`string

Stored scope expected by the operator.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/apiTokens/delete/0" \ -H "Content-Type: application/json" \ -d '{ "expectedScope": "node-sync" }'`

`{ "success": true}`

## Toggle a token enabled/disabled without deleting it. Disabled tokens are rejected by checkAPIAuth on the next request.
POST
/panel/api/setting/apiTokens/setEnabled/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Token row ID.

### Request Body

`application/json`

- body

- body
- …

`enabled*`boolean

New enabled state.

`expectedScope*`string

Stored scope expected by the operator.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/apiTokens/setEnabled/0" \ -H "Content-Type: application/json" \ -d '{ "enabled": false, "expectedScope": "node-sync" }'`

`{ "success": true}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/authentication
# Authentication
Two authentication modes are supported. UI sessions use a cookie set by the login endpoint. Programmatic clients (bots, scripts, remote panels) authenticate with a Bearer token taken from Settings → Security → API Token. Both work for every endpoint under /panel/api/*.

## Authenticate with username + password and receive a session cookie. Required before any cookie-based API call.
POST
/login

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`username*`string

Panel admin username.

`password*`string

Panel admin password.

`twoFactorCode?`string

OTP code when 2FA is enabled. Omit otherwise.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/login" \ -H "Content-Type: application/json" \ -d '{ "username": "admin", "password": "admin", "twoFactorCode": "123456" }'`

`{ "success": true, "msg": "Logged in successfully"}`

## Clear the session cookie. Requires the CSRF header for browser sessions.
POST
/logout

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/logout"`

`{ "success": true}`

## Mint a CSRF token for the current session. The SPA replays it in the X-CSRF-Token header on unsafe requests. Bearer-token callers can skip this — the middleware short-circuits CSRF for authenticated API requests.
GET
/csrf-token

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/csrf-token"`

`{ "success": true, "obj": "csrf-token-string"}`

## Public. Active paid sponsor placements read from the project sponsors.json (cached for 1h); entries outside their from/until window are dropped. Logos are proxied by the panel at /sponsors/logo/{name}. Used by the login page and panel sponsor slots.
GET
/sponsors

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

SponsorList is the active sponsor set plus the contact link for new sponsors.

`curl -X GET "https://example.com/sponsors"`

`{ "success": true, "obj": { "contact": "https://t.me/example", "sponsors": [ { "enable": true, "from": "2026-10-01T00:00:00Z", "id": "acme-2026-10", "link": "https://acme.example/?utm_source=3x-ui", "logo": "/sponsors/logo/acme.png", "name": "Acme VPS", "slots": [ "" ], "text": {}, "title": {}, "until": "2026-11-01T00:00:00Z" } ] }}`

## Returns whether 2FA is enabled on the panel — used by the login page to decide whether to show the OTP field.
POST
/getTwoFactorEnable

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/getTwoFactorEnable"`

`{ "success": true, "obj": false}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/backup
# Backup
Operations that interact with the configured Telegram bot.

## Send a fresh DB backup to every Telegram chat configured as an admin recipient. No body, no params.
POST
/panel/api/backuptotgbot

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/backuptotgbot"`

`{ "success": true, "msg": "string", "obj": null}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/clients
# Clients
Manage clients as first-class entities that can be attached to one or more inbounds. A single client row drives the settings.clients entry in every inbound it belongs to. Endpoints live under /panel/api/clients.

## List every client with its attached inbound IDs and traffic record. The reverse field, if set, is returned as a nested JSON object (legacy JSON-encoded-string form is still accepted on write).
GET
/panel/api/clients/list

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/list"`

`{ "success": true, "obj": [ { "id": 1, "email": "alice@example.com", "subId": "abcd1234", "uuid": "...", "totalGB": 53687091200, "expiryTime": 1735689600000, "enable": true, "reverse": null, "inboundIds": [ 3, 5 ], "traffic": { "up": 1024, "down": 4096, "enable": true } } ]}`

## Filter, sort, and paginate clients on the server. Each item is a slim row (no uuid/password/auth/flow/security/reverse/tgId) so the clients page can ship 25-ish rows in a few KB instead of the full table. The response also includes a summary computed across the full DB row set so dashboard counters stay stable as the user paginates or filters: the *Count fields are exact, while the email arrays beside them stop at 200 entries so the payload does not grow with the panel. Page size capped at 200; fetch /get/:email to obtain the full per-client payload for an edit/info modal.
GET
/panel/api/clients/list/paged

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Query Parameters

`page?`integer

1-indexed page number. Defaults to 1.

Default`1`

`pageSize?`integer

Rows per page. Defaults to 25, capped at 200.

Default`25`

`search?`string

Case-insensitive substring match on email, subId, comment, UUID, password, auth or Telegram ID.

`filter?`string

CSV status buckets: online, active, deactive, depleted or expiring. Values are ORed.

`protocol?`string

CSV inbound protocols: vmess, vless, trojan, shadowsocks, wireguard, hysteria, http, mixed, tunnel, tun, mtproto or amneziawg. Values are ORed.

`inbound?`string

CSV positive inbound IDs. Values are ORed; invalid or non-positive IDs are ignored.

`sort?`string

Sort key. An omitted or unknown value falls back to client ID ascending.

Value in`"enable"``"email"``"inboundIds"``"traffic"``"remaining"``"expiryTime"``"createdAt"``"updatedAt"``"lastOnline"`

`order?`string

Sort direction. Only descend selects descending order; otherwise ascending.

Value in`"ascend"``"descend"`

`expiryFrom?`integer

Inclusive minimum expiry time in Unix milliseconds. Zero or negative means unset.

`expiryTo?`integer

Inclusive maximum expiry time in Unix milliseconds. Zero or negative means unbounded.

`usageFrom?`integer

Inclusive minimum combined upload and download usage in bytes. Zero means unset.

`usageTo?`integer

Inclusive maximum combined upload and download usage in bytes. Zero means unbounded.

`autoRenew?`string

on selects clients with an interval or calendar-day reset; off selects clients without either.

Value in`"on"``"off"`

`hasTgId?`string

yes selects clients with a non-zero Telegram ID; no selects clients without one.

Value in`"yes"``"no"`

`hasComment?`string

yes selects clients with a non-blank comment; no selects clients without one.

Value in`"yes"``"no"`

`group?`string

CSV group names, matched case-insensitively after trimming. Values are ORed.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

ClientPageResponse is the shape returned by ListPaged. `Total` is the
row count in the DB; `Filtered` is the count after Search/Filter/Protocol
were applied, before pagination. The page contains at most PageSize items.
Summary is computed across the full DB row set so dashboard counters
on the clients page stay stable as the user paginates/filters.

`curl -X GET "https://example.com/panel/api/clients/list/paged"`

`{ "success": true, "obj": { "filtered": 47, "groups": [ "staff", "trial" ], "items": [ { "comment": "Primary device", "createdAt": 1735000000000, "email": "alice@example.com", "enable": true, "expiryTime": 1735689600000, "group": "staff", "inboundIds": [ 3, 5 ], "limitHwid": 0, "limitIp": 0, "reset": 0, "resetDay": 0, "resetMax": 0, "resetWeekday": 0, "subId": "abcd1234", "totalGB": 53687091200, "traffic": null, "updatedAt": 1735100000000 } ], "page": 1, "pageSize": 25, "summary": { "active": 1850, "deactive": [ "bob@example.com" ], "deactiveCount": 150, "depleted": [], "depletedCount": 0, "expiring": [], "expiringCount": 0, "online": [ "alice@example.com" ], "onlineCount": 1, "total": 2000 }, "total": 2000 }}`

## Fetch one client by email, including the inbound IDs and external config IDs it is attached to.
GET
/panel/api/clients/get/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique identifier).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/get/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Fetch clients by Telegram user ID. Returns an array since multiple clients can share the same Telegram ID.
GET
/panel/api/clients/get/tgId/{tgId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`tgId*`integer

Telegram user ID (numeric).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/get/tgId/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Create a new client and attach it to one or more inbounds in a single call. Body is JSON. Per-protocol secrets are generated server-side when omitted, so callers can send only the universal fields.
POST
/panel/api/clients/add

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`client*`

Client fields: email, subId, id (uuid), password, auth, flow, totalGB, expiryTime, limitIp, limitHwid, tgId (numeric Telegram user ID, 0 = none), comment, enable. Protocol-specific: secret and adTag (mtproto), privateKey, publicKey, preSharedKey, allowedIPs and keepAlive (WireGuard).

`inboundIds*`array<integer>

Inbound IDs to attach the client to. At least one required.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/add" \ -H "Content-Type: application/json" \ -d '{ "client": { "email": "alice@example.com", "totalGB": 53687091200, "expiryTime": 1735689600000, "tgId": 0, "limitIp": 0, "limitHwid": 0, "enable": true }, "inboundIds": [ 3, 5 ] }'`

`{ "success": true, "msg": "Client added"}`

## Preview client auto-renewal dates without saving or resetting anything.
POST
/panel/api/clients/renewalPreview

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`expiryTime*`integer

Current cutoff in Unix milliseconds; 0 unlimited, negative first-use duration.

`reset*`integer

Fixed interval in days; 0 disabled.

`resetDay*`integer

Monthly calendar day 1-31; 0 disabled.

`resetWeekday*`integer

Weekly calendar day 1-7 (Monday-Sunday); 0 disabled.

`resetMax*`integer

Maximum renewals; 0 unlimited.

`resetCount*`integer

Renewals already consumed; defaults to 0.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X POST "https://example.com/panel/api/clients/renewalPreview" \ -H "Content-Type: application/json" \ -d '{ "expiryTime": 0, "reset": 0, "resetDay": 0, "resetWeekday": 0, "resetMax": 0, "resetCount": 0 }'`

`{ "success": true, "obj": { "canRenew": true, "delayedStart": false, "nextExpiry": "2030-02-01T00:00:00Z", "renewAt": "2030-01-01T00:00:00Z", "renewals": 1, "suggestedExpiry": "2030-01-01T00:00:00Z", "suggestedExpiryTime": 1893456000000, "timeZone": "UTC", "validThrough": "2029-12-31T23:59:59Z" }}`

## Update an existing client by email. Changes propagate to every attached inbound. Body is the JSON client payload — supply the full set of fields you want to keep (the server replaces the row, it does not patch).
POST
/panel/api/clients/update/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Current client email (unique identifier).

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/update/string" \ -H "Content-Type: application/json" \ -d '{ "email": "alice@example.com", "totalGB": 107374182400, "expiryTime": 1767225600000, "limitHwid": 2, "tgId": 123456789, "enable": true }'`

`{ "success": true, "msg": "Client updated"}`

## Delete a client by email. Removes it from every attached inbound and drops its traffic record unless keepTraffic=1 is passed.
POST
/panel/api/clients/del/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique identifier).

### Query Parameters

`keepTraffic*`integer

Pass 1 to retain the xray_client_traffic row after deletion.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/del/string?keepTraffic=0"`

`{ "success": true, "msg": "Client deleted"}`

## Attach an existing client to one or more additional inbounds. Body is JSON.
POST
/panel/api/clients/{email}/attach

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique identifier).

### Request Body

`application/json`

- body

- body
- …

`inboundIds*`array<integer>

Inbound IDs to attach.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/string/attach" \ -H "Content-Type: application/json" \ -d '{ "inboundIds": [ 7, 9 ] }'`

`{ "success": true}`

## Detach a client from one or more inbounds without deleting the client.
POST
/panel/api/clients/{email}/detach

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique identifier).

### Request Body

`application/json`

- body

- body
- …

`inboundIds*`array<integer>

Inbound IDs to detach.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/string/detach" \ -H "Content-Type: application/json" \ -d '{ "inboundIds": [ 5 ] }'`

`{ "success": true}`

## Replace a client's external links and external subscriptions. Sends the full set; the server replaces all rows. Disabled rows stay saved for editing but are not emitted in generated subscriptions. The owning client's disabled or expired state also stops these rows from being emitted on future subscription fetches; credentials already imported by an app remain valid until the external provider revokes them.
POST
/panel/api/clients/{email}/externalLinks

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique identifier).

### Request Body

`application/json`

- body

- body
- …

`externalLinks*`array<>

Full replacement list; the server replaces all rows. Each row supports { kind, value, remark, enable, expiryTime, namePrefix }. kind=link: value must be a supported share link such as vless://, vmess://, trojan://, ss://, hysteria2://, or wireguard://, and remark overrides the exported node name. kind=subscription: value must be an http(s) subscription URL, and namePrefix is prepended to fetched node names. Omit enable to default true; enable=false or an expired expiryTime keeps the row saved but excludes it from generated subscriptions. expiryTime is a unix millisecond timestamp where 0 means no link-specific expiry; the owning client's enabled state and expiry still apply. A negative value is rejected. Rows are matched by kind+value across saves, so id is ignored on write. lastFetchAt and lastFetchError are read-only status fields returned by GET.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/string/externalLinks" \ -H "Content-Type: application/json" \ -d '{ "externalLinks": [ { "kind": "link", "value": "vless://uuid@host:443?...#srv", "remark": "DE", "enable": true, "expiryTime": 0 }, { "kind": "subscription", "value": "https://provider.example/sub/abc", "remark": "Provider", "enable": false, "expiryTime": 1767225600000, "namePrefix": "[zjh] " } ] }'`

`{ "success": true}`

## Reset the up/down counters for every client globally. Quotas and expiry are not affected. Triggers an Xray restart if any counter actually moved.
POST
/panel/api/clients/resetAllTraffics

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/resetAllTraffics"`

`{ "success": true}`

## Delete every client whose traffic quota is exhausted (used >= total, when reset is disabled) or whose expiry has passed. Returns the deleted count and triggers an Xray restart when any client was on a running inbound.
POST
/panel/api/clients/delDepleted

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/delDepleted"`

`{ "success": true, "obj": { "deleted": 0 }}`

## Delete every client that is not attached to any inbound, along with its traffic record, IP log, HWID devices, and external links. Useful for clearing clients left unattached after their inbounds were removed. Returns the deleted count. Cannot be undone.
POST
/panel/api/clients/delOrphans

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/delOrphans"`

`{ "success": true, "obj": { "deleted": 0 }}`

## Return every client as a {client, inboundIds, traffic} array — the shape /import accepts — so the payload round-trips straight back through /import. traffic carries the usage counters (up, down, resetCount, lastOnline, lastSubFetch) and is omitted for a client with no traffic row; the quota itself stays in client.totalGB. Clients with no inbound attachment are included with an empty inboundIds list. The UI shows this in a CodeMirror viewer (copy / download); programmatic callers get the array in obj.
GET
/panel/api/clients/export

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/export"`

`{ "success": true, "obj": [ { "client": { "email": "alice@example.com", "id": "...", "totalGB": 53687091200, "expiryTime": 0, "limitHwid": 2, "enable": true, "subId": "..." }, "inboundIds": [ 7, 9 ], "traffic": { "up": 1048576, "down": 2097152, "resetCount": 0, "lastOnline": 1735680000000 } } ]}`

## Import clients from a JSON body { "data": "<json>" }, where data is a string-encoded array produced by /export ([{client, inboundIds, traffic}]). Items with inboundIds are created and attached to those inbounds; items with an empty inboundIds list are restored as unattached client records. An optional traffic object restores the usage counters, only for clients this import creates. Existing emails are never overwritten — they are returned in skipped, and their live counters are left untouched. Triggers a single Xray restart at the end if any target inbound was running; a failure while restoring counters still reports success=false after the clients were created.
POST
/panel/api/clients/import

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/import" \ -H "Content-Type: application/json" \ -d '{ "data": "[{\\"client\\":{\\"email\\":\\"alice@example.com\\",\\"enable\\":true},\\"inboundIds\\":[7]}]" }'`

`{ "success": true, "obj": { "created": 2, "skipped": [ { "email": "alice@example.com", "reason": "email already in use: alice@example.com" } ] }}`

## Shift expiry and/or traffic quota for many clients in one call. addDays/addBytes may be negative. Clients with unlimited expiry (expiryTime=0) or unlimited traffic (totalGB=0) are skipped for the corresponding field — bulk extend never converts unlimited to limited. A client that was auto-disabled solely because it was depleted (expired or over quota) is automatically re-enabled — locally and on its node — when the adjustment lifts it out of depletion; a manually-disabled or still-depleted client is left disabled. The optional flow directive sets the XTLS flow on every client: "none" clears it, "xtls-rprx-vision"/"xtls-rprx-vision-udp443" set it where the inbound supports it (omit or "" to leave it unchanged). The optional limitHwid sets maximum registered devices (0 = unlimited). The optional adTag sets MTProto Telegram sponsor channel ("none" clears). Returns the adjusted count and per-email skip reasons.
POST
/panel/api/clients/bulkAdjust

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkAdjust" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ], "addDays": 30, "addBytes": 53687091200, "flow": "xtls-rprx-vision", "limitHwid": 2, "adTag": "0123456789abcdef0123456789abcdef" }'`

`{ "success": true, "obj": { "adjusted": 2, "skipped": [ { "email": "carol", "reason": "unlimited expiry" } ] }}`

## Enable many clients in one call. Emails are grouped by inbound and applied with a single read-modify-write per inbound; the running Xray (local or remote node) is updated to add each user. Note that enabling a client whose quota is exhausted or whose expiry has passed only flips the flag — the traffic loop will disable it again on the next tick. Returns the changed count and per-email skip reasons.
POST
/panel/api/clients/bulkEnable

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkEnable" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ] }'`

`{ "success": true, "obj": { "changed": 2, "skipped": [ { "email": "carol", "reason": "client not found" } ] }}`

## Disable many clients in one call. Emails are grouped by inbound and applied with a single read-modify-write per inbound; the running Xray (local or remote node) is updated to remove each user. Returns the changed count and per-email skip reasons.
POST
/panel/api/clients/bulkDisable

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkDisable" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ] }'`

`{ "success": true, "obj": { "changed": 2, "skipped": [ { "email": "carol", "reason": "client not found" } ] }}`

## Delete many clients in one call. The server processes the list sequentially so each delete sees the committed state of the previous one — avoids the race the per-email fan-out had on the panel side. Pass keepTraffic=true to retain the xray_client_traffic rows after deletion.
POST
/panel/api/clients/bulkDel

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkDel" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ], "keepTraffic": false }'`

`{ "success": true, "obj": { "deleted": 2, "skipped": [ { "email": "carol", "reason": "client not found" } ] }}`

## Create many clients in one call. Body is a JSON array of {client, inboundIds} payloads — the same shape /add accepts. Items are processed sequentially; per-email skip reasons are returned for items that fail (e.g., duplicate email). Triggers a single Xray restart at the end if any inbound was running.
POST
/panel/api/clients/bulkCreate

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkCreate" \ -H "Content-Type: application/json" \ -d '[ { "client": { "email": "alice@example.com", "totalGB": 53687091200, "expiryTime": 0, "limitHwid": 2, "enable": true }, "inboundIds": [ 7 ] }, { "client": { "email": "bob@example.com", "totalGB": 53687091200, "expiryTime": 0, "limitHwid": 0, "enable": true }, "inboundIds": [ 7, 9 ] } ]'`

`{ "success": true, "obj": { "created": 2, "skipped": [ { "email": "alice@example.com", "reason": "email already in use" } ] }}`

## Add many clients to a group in one call. Updates clients.group_name and patches the matching client entry inside every owning inbound's settings JSON in a single transaction. If the group name does not yet exist (in client_groups or as a derived label), it is auto-created as a persistent group. To clear the group label, use /groups/bulkRemove instead.
POST
/panel/api/clients/groups/bulkAdd

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/groups/bulkAdd" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ], "group": "customer-a" }'`

`{ "success": true, "obj": { "affected": 2 }}`

## Clear the group label on many clients in one call. Inverse of /groups/bulkAdd. Clients themselves are kept — only the group label is cleared from clients.group_name and from each owning inbound's settings JSON. Groups become empty if all their members are removed.
POST
/panel/api/clients/groups/bulkRemove

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/groups/bulkRemove" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ] }'`

`{ "success": true, "obj": { "affected": 2 }}`

## Attach many existing clients to many inbounds in one call. Each client keeps its identity (email/UUID/password/subId) and a shared traffic row; all clients are added to a target inbound in a single AddInboundClient call. Clients already present on a target are reported under skipped. Returns per-email attached/skipped/errors lists and triggers a single Xray restart if any target inbound was running.
POST
/panel/api/clients/bulkAttach

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`emails*`array<string>

Emails of existing clients to attach.

`inboundIds*`array<integer>

Target inbound IDs to attach every client to.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkAttach" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ], "inboundIds": [ 7, 9 ] }'`

`{ "success": true, "obj": { "attached": [ "alice", "bob" ], "skipped": [ "bob" ], "errors": [] }}`

## Mirror of bulkAttach: detach many existing clients from many inbounds in one call. For each email, intersects the client's current inbounds with the requested set and detaches from those only; (email, inbound) pairs where the client is not currently attached are silently no-ops. Emails not attached to any of the requested inbounds are reported under skipped. Client records are kept even if they become orphaned — use bulkDel for full removal. Returns per-email detached/skipped/errors lists and triggers a single Xray restart if any target inbound was running.
POST
/panel/api/clients/bulkDetach

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`emails*`array<string>

Emails of existing clients to detach.

`inboundIds*`array<integer>

Inbound IDs to detach the clients from.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkDetach" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ], "inboundIds": [ 7, 9 ] }'`

`{ "success": true, "obj": { "detached": [ "alice", "bob" ], "skipped": [], "errors": [] }}`

## Zero up/down counters for many clients in one call. Loops the single-reset path so each client is re-enabled across its attached inbounds and pushed to Xray/remote nodes. Returns the count of successfully reset clients.
POST
/panel/api/clients/bulkResetTraffic

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/bulkResetTraffic" \ -H "Content-Type: application/json" \ -d '{ "emails": [ "alice", "bob" ] }'`

`{ "success": true, "obj": { "affected": 2 }}`

## List all client groups with their member counts. Merges persisted groups (rows in client_groups, including empty placeholders) with the distinct group_name values currently set on clients. Sorted alphabetically (case-insensitive).
GET
/panel/api/clients/groups

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/groups"`

`{ "success": true, "obj": [ { "name": "customer-a", "clientCount": 5 }, { "name": "internal", "clientCount": 0 } ]}`

## Return just the email list of clients that currently belong to the given group. Useful for fanning a single bulk action over an entire group without round-tripping the full client list.
GET
/panel/api/clients/groups/{name}/emails

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`name*`string

Group name (URL-encoded).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/groups/string/emails"`

`{ "success": true, "obj": [ "alice", "bob", "carol" ]}`

## Create a new empty (placeholder) group. The group becomes selectable in client forms and the filter drawer even before any client is added to it. Errors if a group with the same name already exists.
POST
/panel/api/clients/groups/create

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/groups/create" \ -H "Content-Type: application/json" \ -d '{ "name": "customer-a" }'`

`{ "success": true, "obj": { "name": "customer-a" }}`

## Rename a group. The new name is applied to the client_groups row AND propagated to every matching client (both clients.group_name and the client entry inside every owning inbound's settings JSON) in a single transaction. Returns the number of clients whose label was updated.
POST
/panel/api/clients/groups/rename

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/groups/rename" \ -H "Content-Type: application/json" \ -d '{ "oldName": "customer-a", "newName": "tier-1" }'`

`{ "success": true, "obj": { "affected": 5 }}`

## Remove a group. Deletes the client_groups row and clears the group label from every matching client (both clients.group_name and the inbound settings JSON). The clients themselves are NOT deleted — use /bulkDel after filtering by group for that. Returns the count of clients whose label was cleared.
POST
/panel/api/clients/groups/delete

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/groups/delete" \ -H "Content-Type: application/json" \ -d '{ "name": "customer-a" }'`

`{ "success": true, "obj": { "affected": 5 }}`

## Reset only the group-level traffic counter shown on the groups page. Snapshots the current up/down sum of the group's members as a baseline so the group total reads zero, while leaving each client's own counters (and their quotas) untouched. No Xray restart is triggered. Creates the client_groups row if the group exists only as a derived label.
POST
/panel/api/clients/groups/resetTraffic

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/groups/resetTraffic" \ -H "Content-Type: application/json" \ -d '{ "name": "customer-a" }'`

`{ "success": true, "obj": { "name": "customer-a" }}`

## Zero out a single client’s up/down counters. Re-enables the client across every attached inbound and pushes the change to Xray (or the remote node) so depleted users can connect again immediately.
POST
/panel/api/clients/resetTraffic/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/resetTraffic/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Manually adjust a client’s upload + download counters. Useful for migrations from external accounting systems.
POST
/panel/api/clients/updateTraffic/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/updateTraffic/string" \ -H "Content-Type: application/json" \ -d '{ "upload": 1073741824, "download": 5368709120 }'`

`{ "success": true, "msg": "string", "obj": null}`

## List source IPs that have connected with the given client’s credentials. Returns an array of "ip (timestamp)" strings.
POST
/panel/api/clients/ips/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/ips/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Reset the recorded IP list for a client.
POST
/panel/api/clients/clearIps/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/clearIps/string"`

`{ "success": true, "msg": "string", "obj": null}`

## List registered HWID devices for a client with a short fingerprint. Full hashes are not exposed.
POST
/panel/api/clients/hwids/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/hwids/string"`

`{ "success": true, "obj": [ { "id": 1, "firstSeen": 1735000000000, "lastSeen": 1735100000000, "userAgent": "Happ/1.0", "deviceOs": "android", "osVersion": "15", "deviceModel": "Pixel 9", "fingerprint": "6ad17c93e821" } ]}`

## Clear all registered HWID devices for a client so new devices can register again.
DELETE
/panel/api/clients/hwids/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X DELETE "https://example.com/panel/api/clients/hwids/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Remove a single registered HWID device by its id, freeing one slot under the HWID limit.
DELETE
/panel/api/clients/hwids/{email}/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email.

`id*`integer

Device id, from the list endpoint.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X DELETE "https://example.com/panel/api/clients/hwids/string/0"`

`{ "success": true, "msg": "string", "obj": null}`

## List the emails of currently connected clients (last seen within the heartbeat window), deduped across every node.
POST
/panel/api/clients/onlines

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/onlines"`

`{ "success": true, "obj": [ "user1", "user2" ]}`

## Online client emails grouped by the panelGuid of the node that physically hosts each client. The local panel uses its own GUID; each node (at any depth in a chain) uses its GUID. Lets the inbounds page attribute online status to the real node instead of the intermediate one it syncs through.
POST
/panel/api/clients/onlinesByGuid

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/onlinesByGuid"`

`{ "success": true, "obj": { "a1b2-...": [ "user1" ], "c3d4-...": [ "user1", "user2" ] }}`

## Per-client source IPs grouped by the panelGuid of the node that observed them. Lets the central panel attribute and enforce per-client IP limits using the real visitor IPs each node sees, instead of the address of the intermediate panel it syncs through.
POST
/panel/api/clients/clientIpsByGuid

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/clientIpsByGuid"`

`{ "success": true, "obj": { "a1b2-...": { "user1": [ { "ip": "1.2.3.4", "timestamp": 1700000000 } ] } }}`

## Inbound tags that carried traffic within the heartbeat window, grouped by the hosting node's panelGuid. Pairs with onlinesByGuid so the inbounds page only marks a multi-inbound client online on the inbounds it actually used. Nodes that do not report per-inbound activity are absent.
POST
/panel/api/clients/activeInbounds

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/activeInbounds"`

`{ "success": true, "obj": { "a1b2-...": [ "in-443-tcp", "in-8443-tcp" ] }}`

## Map of client email → last-seen unix timestamp.
POST
/panel/api/clients/lastOnline

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/clients/lastOnline"`

`{ "success": true, "obj": { "user1": 1700000000, "user2": 1699999000 }}`

## Traffic counters for a client identified by email.
GET
/panel/api/clients/traffic/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique across the panel).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

ClientTraffic represents traffic statistics and limits for a specific client.
It tracks upload/download usage, expiry times, and online status for inbound clients.

`curl -X GET "https://example.com/panel/api/clients/traffic/string"`

`{ "success": true, "obj": { "down": 2097152, "email": "user1", "enable": true, "expiryTime": 1735689600000, "id": 14825, "inboundId": 1, "lastOnline": 1735680000000, "lastSubFetch": 1735680000000, "reset": 0, "resetCount": 0, "resetDay": 0, "resetMax": 0, "resetWeekday": 0, "subId": "i7tvdpeffi0hvvf1", "total": 10737418240, "up": 1048576, "uuid": "e18c9a96-71bf-48d4-933f-8b9a46d4290c" }}`

## Return every protocol URL (vless://, vmess://, trojan://, ss://, hysteria://, hy2://) for clients matching the subscription ID. Same result set as the configured subPath endpoint, but as a JSON array — no base64. When an inbound has streamSettings.externalProxy set, one URL is emitted per external proxy. Empty array when the subId has no enabled clients.
GET
/panel/api/clients/subLinks/{subId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subId*`string

Subscription ID, taken from the client's subId field.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/subLinks/string"`

`{ "success": true, "obj": [ "vless://uuid@host:443?security=reality&...#user1", "vmess://eyJ2IjoyLC..." ]}`

## Generate a fresh Happ crypt5 link locally from the current client subscription URL when Happ link generation is enabled. The panel applies a resource limit of 8192 UTF-8 bytes to the source URL; this is not a Happ client maximum. Longer sources return success: false with msg: happ_source_too_long and obj: null. The source URL is not sent to a generation provider, and the result is not stored or reused.
POST
/panel/api/clients/happLink/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Stable client record ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X POST "https://example.com/panel/api/clients/happLink/0"`

`{ "success": true, "obj": { "encryptedLink": "happ://crypt5/example" }}`

## Return every URL for one client across all attached inbounds, one per advertised endpoint: the managed hosts of the inbound, else its streamSettings.externalProxy entries, else its own address. Supported protocols: vmess, vless, trojan, shadowsocks, hysteria, mtproto. Protocols without a URL form (socks, http, mixed, wireguard, dokodemo, tunnel) contribute nothing.
GET
/panel/api/clients/links/{email}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`email*`string

Client email (unique identifier).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/clients/links/string"`

`{ "success": true, "obj": [ "vless://uuid@host:443?...#user1" ]}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/hosts
# Hosts
Per-inbound override endpoints. Each enabled host renders one extra subscription link/proxy with its own address/port/TLS, superseding the legacy externalProxy array. All endpoints under /panel/api/hosts.

## List every host across all inbounds, grouped by inbound then ordered by sort order.
GET
/panel/api/hosts/list

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/hosts/list"`

`{ "success": true, "obj": [ { "allowInsecure": false, "alpn": [ "" ], "cipherSuites": "", "echConfigList": "", "excludeFromSubTypes": [ "" ], "finalMask": "", "fingerprint": "", "groupId": "", "hostHeader": "", "hosts": [ "" ], "inboundIds": [ 0 ], "isDisabled": false, "isHidden": false, "keepSniBlank": false, "mihomoIpVersion": "dual", "mihomoX25519": false, "muxParams": "", "nodeGuids": [ "" ], "overrideSniFromAddress": false, "path": "", "pinnedPeerCertSha256": [ "" ], "port": 0, "remark": "", "security": "same", "serverDescription": "", "shuffleHost": false, "sni": "", "sockoptParams": "", "sortOrder": 0, "tags": [ "" ], "verifyPeerCertByName": "", "vlessRoute": "" } ]}`

## Fetch a single host group by Group ID.
GET
/panel/api/hosts/get/{groupId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`groupId*`string

Host Group ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X GET "https://example.com/panel/api/hosts/get/string"`

`{ "success": true, "obj": { "allowInsecure": false, "alpn": [ "" ], "cipherSuites": "", "echConfigList": "", "excludeFromSubTypes": [ "" ], "finalMask": "", "fingerprint": "", "groupId": "", "hostHeader": "", "hosts": [ "" ], "inboundIds": [ 0 ], "isDisabled": false, "isHidden": false, "keepSniBlank": false, "mihomoIpVersion": "dual", "mihomoX25519": false, "muxParams": "", "nodeGuids": [ "" ], "overrideSniFromAddress": false, "path": "", "pinnedPeerCertSha256": [ "" ], "port": 0, "remark": "", "security": "same", "serverDescription": "", "shuffleHost": false, "sni": "", "sockoptParams": "", "sortOrder": 0, "tags": [ "" ], "verifyPeerCertByName": "", "vlessRoute": "" }}`

## Fetch one inbound's hosts, grouped by host group.
GET
/panel/api/hosts/byInbound/{inboundId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`inboundId*`integer

Inbound ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/hosts/byInbound/0"`

`{ "success": true, "obj": [ { "allowInsecure": false, "alpn": [ "" ], "cipherSuites": "", "echConfigList": "", "excludeFromSubTypes": [ "" ], "finalMask": "", "fingerprint": "", "groupId": "", "hostHeader": "", "hosts": [ "" ], "inboundIds": [ 0 ], "isDisabled": false, "isHidden": false, "keepSniBlank": false, "mihomoIpVersion": "dual", "mihomoX25519": false, "muxParams": "", "nodeGuids": [ "" ], "overrideSniFromAddress": false, "path": "", "pinnedPeerCertSha256": [ "" ], "port": 0, "remark": "", "security": "same", "serverDescription": "", "shuffleHost": false, "sni": "", "sockoptParams": "", "sortOrder": 0, "tags": [ "" ], "verifyPeerCertByName": "", "vlessRoute": "" } ]}`

## Distinct, sorted set of tags used across all hosts.
GET
/panel/api/hosts/tags

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/hosts/tags"`

`{ "success": true, "obj": [ "CDN", "EU", "FAST" ]}`

## Create a host group on inbounds.
POST
/panel/api/hosts/add

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X POST "https://example.com/panel/api/hosts/add" \ -H "Content-Type: application/json" \ -d '{ "inboundIds": [ 1 ], "remark": "cdn-front", "hosts": [ "cdn.example.com" ], "port": 8443, "security": "same", "tags": [ "CDN" ] }'`

`{ "success": true, "obj": [ { "address": "cdn.example.com", "allowInsecure": false, "alpn": [ "" ], "cipherSuites": "", "createdAt": 0, "echConfigList": "", "excludeFromSubTypes": [ "" ], "finalMask": "", "fingerprint": "", "groupId": "", "hostHeader": "", "id": 1, "inboundId": 1, "isDisabled": false, "isHidden": false, "keepSniBlank": false, "mihomoIpVersion": "dual", "mihomoX25519": false, "muxParams": null, "nodeGuids": [ "" ], "overrideSniFromAddress": false, "path": "", "pinnedPeerCertSha256": [ "" ], "port": 8443, "remark": "cdn-front", "security": "same", "serverDescription": "", "shuffleHost": false, "sni": "", "sockoptParams": null, "sortOrder": 0, "tags": [ "" ], "updatedAt": 0, "verifyPeerCertByName": "", "vlessRoute": "443" } ]}`

## Replace a host group’s content.
POST
/panel/api/hosts/update/{groupId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`groupId*`string

Host Group ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X POST "https://example.com/panel/api/hosts/update/string" \ -H "Content-Type: application/json" \ -d '{ "inboundIds": [ 1 ], "remark": "cdn-front", "hosts": [ "cdn.example.com" ], "port": 8443, "security": "same", "tags": [ "CDN" ] }'`

`{ "success": true, "obj": [ { "address": "cdn.example.com", "allowInsecure": false, "alpn": [ "" ], "cipherSuites": "", "createdAt": 0, "echConfigList": "", "excludeFromSubTypes": [ "" ], "finalMask": "", "fingerprint": "", "groupId": "", "hostHeader": "", "id": 1, "inboundId": 1, "isDisabled": false, "isHidden": false, "keepSniBlank": false, "mihomoIpVersion": "dual", "mihomoX25519": false, "muxParams": null, "nodeGuids": [ "" ], "overrideSniFromAddress": false, "path": "", "pinnedPeerCertSha256": [ "" ], "port": 8443, "remark": "cdn-front", "security": "same", "serverDescription": "", "shuffleHost": false, "sni": "", "sockoptParams": null, "sortOrder": 0, "tags": [ "" ], "updatedAt": 0, "verifyPeerCertByName": "", "vlessRoute": "443" } ]}`

## Delete a host group.
POST
/panel/api/hosts/del/{groupId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`groupId*`string

Host Group ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/hosts/del/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Enable or disable a host group.
POST
/panel/api/hosts/setEnable/{groupId}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`groupId*`string

Host Group ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/hosts/setEnable/string" \ -H "Content-Type: application/json" \ -d '{ "enable": true }'`

`{ "success": true, "msg": "string", "obj": null}`

## Set host group sort order by the position of each groupId in the array.
POST
/panel/api/hosts/reorder

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/hosts/reorder" \ -H "Content-Type: application/json" \ -d '{ "ids": [ "abc-123", "def-456" ] }'`

`{ "success": true, "msg": "string", "obj": null}`

## Add a host group to inbounds (same as /add).
POST
/panel/api/hosts/bulk/add

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X POST "https://example.com/panel/api/hosts/bulk/add" \ -H "Content-Type: application/json" \ -d '{ "inboundIds": [ 1, 2 ], "hosts": [ "cdn.example.com", "cdn2.example.com:443" ], "remark": "Cloudflare CDN", "port": 0, "security": "same", "isDisabled": false }'`

`{ "success": true, "obj": [ { "address": "cdn.example.com", "allowInsecure": false, "alpn": [ "" ], "cipherSuites": "", "createdAt": 0, "echConfigList": "", "excludeFromSubTypes": [ "" ], "finalMask": "", "fingerprint": "", "groupId": "", "hostHeader": "", "id": 1, "inboundId": 1, "isDisabled": false, "isHidden": false, "keepSniBlank": false, "mihomoIpVersion": "dual", "mihomoX25519": false, "muxParams": null, "nodeGuids": [ "" ], "overrideSniFromAddress": false, "path": "", "pinnedPeerCertSha256": [ "" ], "port": 8443, "remark": "cdn-front", "security": "same", "serverDescription": "", "shuffleHost": false, "sni": "", "sockoptParams": null, "sortOrder": 0, "tags": [ "" ], "updatedAt": 0, "verifyPeerCertByName": "", "vlessRoute": "443" } ]}`

## Enable or disable many host groups in one call.
POST
/panel/api/hosts/bulk/setEnable

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/hosts/bulk/setEnable" \ -H "Content-Type: application/json" \ -d '{ "ids": [ "abc-123", "def-456" ], "enable": false }'`

`{ "success": true, "msg": "string", "obj": null}`

## Delete many host groups in one call.
POST
/panel/api/hosts/bulk/del

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/hosts/bulk/del" \ -H "Content-Type: application/json" \ -d '{ "ids": [ "abc-123", "def-456" ] }'`

`{ "success": true, "msg": "string", "obj": null}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/inbounds
# Inbounds
Manage inbound configurations and their clients. All endpoints live under /panel/api/inbounds and require a logged-in session or Bearer token. Link-generating endpoints honour forwarded headers only when the request comes from a configured trusted proxy.

## List every inbound owned by the authenticated user, including each inbound’s clientStats traffic counters. settings, streamSettings, and sniffing are returned as nested JSON objects (no escaped strings); legacy callers that send them back as JSON-encoded strings are still accepted on write.
GET
/panel/api/inbounds/list

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/inbounds/list"`

`{ "success": true, "obj": [ { "clientStats": [ { "down": 2097152, "email": "user1", "enable": true, "expiryTime": 1735689600000, "id": 14825, "inboundId": 1, "lastOnline": 1735680000000, "lastSubFetch": 1735680000000, "reset": 0, "resetCount": 0, "resetDay": 0, "resetMax": 0, "resetWeekday": 0, "subId": "i7tvdpeffi0hvvf1", "total": 10737418240, "up": 1048576, "uuid": "e18c9a96-71bf-48d4-933f-8b9a46d4290c" } ], "disableFlow": false, "down": 0, "enable": true, "excludeFromSub": false, "expiryTime": 0, "fallbackParent": null, "id": 1, "lastTrafficResetTime": 0, "listen": "", "nodeId": null, "originNodeGuid": "", "port": 443, "protocol": "vless", "remark": "VLESS-443", "settings": null, "shareAddr": "", "shareAddrStrategy": "node", "sniffing": null, "streamSettings": null, "subSortIndex": 1, "tag": "in-443-tcp", "total": 0, "trafficReset": "never", "trafficResetDay": 1, "up": 0 } ]}`

## Same shape as /list but with settings.clients[] stripped down to {email, enable, comment} and ClientStats not enriched with UUID/SubId. Use this for list pages; fetch /get/:id when you need the full per-client payload (uuid, password, flow, ...).
GET
/panel/api/inbounds/list/slim

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/inbounds/list/slim"`

`{ "success": true, "obj": [ { "id": 1, "remark": "VLESS-443", "settings": { "clients": [ { "email": "alice", "enable": true } ], "decryption": "none" }, "clientStats": [] } ]}`

## Lightweight picker projection of the authenticated user’s inbounds. Returns id, remark, tag, protocol, port, a server-computed tlsFlowCapable flag (true for VLESS on TCP with tls or reality, or on XHTTP with VLESS encryption / vlessenc enabled), and ssMethod (the Shadowsocks cipher, empty for non-Shadowsocks inbounds — used by the client UI to generate a valid Shadowsocks 2022 PSK). Use this for dropdowns and attach pickers — it skips settings, streamSettings, and clientStats so the payload stays small even on panels with thousands of clients.
GET
/panel/api/inbounds/options

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/inbounds/options"`

`{ "success": true, "obj": [ { "awgServer": null, "enable": true, "id": 1, "listen": "", "mtprotoDomain": "", "network": "", "nodeAddress": "", "nodeId": null, "port": 443, "protocol": "vless", "remark": "VLESS-443", "security": "", "shareAddr": "", "shareAddrStrategy": "", "ssMethod": "", "tag": "in-443-tcp", "tlsFlowCapable": true, "tuicServer": null, "wgDns": "", "wgMtu": 0, "wgPublicKey": "" } ]}`

## Return every protocol URL (vless://, vmess://, trojan://, ss://, hysteria://, mtproto) across all inbounds and all of their clients. Links are rendered through the subscription engine, so the configured remark template (name-only display part) is applied per client — the same output the client info/QR pages use. Protocols without a URL form (socks, http, mixed, wireguard, dokodemo, tunnel) contribute nothing. Used by the panel’s "Export all inbound links" action.
GET
/panel/api/inbounds/allLinks

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<string>|null

`curl -X GET "https://example.com/panel/api/inbounds/allLinks"`

`{ "success": true, "obj": [ "vless://uuid@host:443?security=reality&...#Germany-alice", "vmess://eyJ2IjoyLC..." ]}`

## Fetch a single inbound by numeric ID.
GET
/panel/api/inbounds/get/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/inbounds/get/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Create a new inbound. Send the full inbound payload (protocol, port, settings, streamSettings, sniffing, remark, expiryTime, total, enable). settings, streamSettings, and sniffing may be sent as nested JSON objects (preferred) or as JSON-encoded strings (legacy).
POST
/panel/api/inbounds/add

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/add" \ -H "Content-Type: application/json" \ -d '{ "enable": true, "remark": "VLESS-443", "listen": "", "port": 443, "protocol": "vless", "expiryTime": 0, "total": 0, "settings": { "clients": [ { "id": "...", "email": "user1" } ], "decryption": "none", "fallbacks": [] }, "streamSettings": { "network": "tcp", "security": "reality", "realitySettings": { "show": false, "dest": "..." } }, "sniffing": { "enabled": true, "destOverride": [ "http", "tls" ] } }'`

`{ "success": true, "msg": "string", "obj": null}`

## Delete an inbound by ID. Also removes its associated client stats rows.
POST
/panel/api/inbounds/del/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/del/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Delete many inbounds in one call. Processes the list sequentially; failures are reported per id and the rest still proceed. Restarts xray at most once.
POST
/panel/api/inbounds/bulkDel

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/bulkDel" \ -H "Content-Type: application/json" \ -d '{ "ids": [ 1, 2, 3 ] }'`

`{ "success": true, "obj": { "deleted": 2, "skipped": [ { "id": 3, "reason": "..." } ] }}`

## Replace an inbound’s configuration. Body shape mirrors /add, but the inbound keeps its stored client list and enable flag: settings.clients and enable in the body are ignored. Manage clients through the /panel/api/clients endpoints and toggle the inbound with /setEnable.
POST
/panel/api/inbounds/update/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/update/0" \ -H "Content-Type: application/json" \ -d '{ "enable": true, "remark": "VLESS-443", "listen": "", "port": 443, "protocol": "vless", "expiryTime": 0, "total": 0, "settings": { "clients": [ { "id": "...", "email": "user1" } ], "decryption": "none", "fallbacks": [] }, "streamSettings": { "network": "tcp", "security": "reality", "realitySettings": { "show": false, "dest": "..." } }, "sniffing": { "enabled": true, "destOverride": [ "http", "tls" ] } }'`

`{ "success": true, "msg": "string", "obj": null}`

## Toggle only the enable flag without serialising the whole settings JSON. Recommended for UI switches on large inbounds.
POST
/panel/api/inbounds/setEnable/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/setEnable/0" \ -H "Content-Type: application/json" \ -d '{ "enable": false }'`

`{ "success": true, "msg": "string", "obj": null}`

## Set only the subscription sort order. Reads the stored inbound, so a reorder cannot carry a stale client list over a concurrent edit.
POST
/panel/api/inbounds/{id}/subSortIndex

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/0/subSortIndex" \ -H "Content-Type: application/json" \ -d '{ "subSortIndex": 2 }'`

`{ "success": true, "msg": "string", "obj": null}`

## Zero out upload + download counters for a single inbound. Does not touch per-client counters.
POST
/panel/api/inbounds/{id}/resetTraffic

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/0/resetTraffic"`

`{ "success": true, "msg": "string", "obj": null}`

## Remove every client attached to a single inbound while keeping the inbound itself. Collects emails from settings.clients[] and feeds them into the optimized bulk-delete path (runtime user removal + traffic-row cleanup + SyncInbound). Destructive and cannot be undone.
POST
/panel/api/inbounds/{id}/delAllClients

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Inbound ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/0/delAllClients"`

`{ "success": true, "obj": { "deleted": 12 }}`

## Reset upload + download counters on every inbound. Destructive — accounting history is lost.
POST
/panel/api/inbounds/resetAllTraffics

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/resetAllTraffics"`

`{ "success": true, "msg": "string", "obj": null}`

## Bulk-import an inbound from a JSON blob (e.g. one exported via the UI). The body uses form encoding with a single "data" field.
POST
/panel/api/inbounds/import

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`data*`string

JSON-encoded inbound payload.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/import" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'data=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Receive a master panel's aggregated per-client usage, keyed by the master's GUID. Stored in a side table used only for the UI display overlay and local quota enforcement — never folded into the local counters that masters poll, so delta accounting stays intact. Called panel-to-panel by the node traffic sync job.
POST
/panel/api/inbounds/pushClientTraffics

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`masterGuid*`string

Stable GUID of the pushing master panel.

`traffics*`array<>

Client traffic rows; only email/up/down are read.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/pushClientTraffics" \ -H "Content-Type: application/json" \ -d '{ "masterGuid": "9f6c2d-…", "traffics": [ { "email": "alice", "up": 1048576, "down": 2097152 } ] }'`

`{ "success": true}`

## List the fallback rules attached to a master VLESS/Trojan TCP-TLS inbound. Each rule links one child inbound (the dest) to optional SNI/ALPN/path/dest/xver match criteria. When dest is empty the child inbound's listen+port is used.
GET
/panel/api/inbounds/{id}/fallbacks

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Master inbound ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/inbounds/0/fallbacks"`

`{ "success": true, "obj": [ { "id": 1, "masterId": 10, "childId": 11, "name": "", "alpn": "", "path": "/vlws", "dest": "", "xver": 2, "sortOrder": 0 } ]}`

## Replace the entire fallback list for a master inbound. Body is JSON. Triggers an Xray restart.
POST
/panel/api/inbounds/{id}/fallbacks

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Master inbound ID.

### Request Body

`application/json`

- body

- body
- …

`fallbacks*`array<>

Array of {childId, name, alpn, path, dest, xver, sortOrder} entries. Leave dest empty to auto-resolve from the child inbound's listen+port; set it (e.g. "8443", "127.0.0.1:8443", "/dev/shm/x.sock") to override.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/inbounds/0/fallbacks" \ -H "Content-Type: application/json" \ -d '{ "fallbacks": [ { "childId": 11, "path": "/vlws", "xver": 2 }, { "childId": 12, "alpn": "h2", "dest": "8443" } ] }'`

`{ "success": true, "msg": "Inbound updated"}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api
# API Reference
The 3x-ui panel REST API — authentication, inbounds, clients, server stats, and more, generated from the OpenAPI spec.

The 3x-ui panel exposes a REST API for automation. These pages are generated from
the panel's OpenAPI specification, so they always match the documented schema.

## Authentication

Requests authenticate with either a session cookie (from `POST /login`) or a
Bearer token:

`Authorization: Bearer <token>`

Create API tokens in the panel; they are full-admin credentials, so store them
securely. See API Tokens.

Build an authenticated request for any endpoint below:

### 

Panel base URL
API token (Bearer)
Endpoint path
MethodGETPOSTPUTDELETE

cURL
`curl -X GET 'https://panel.example.com:2053/panel/api/inbounds/list' \
 -H 'Authorization: Bearer <token>'`

fetch()
`await fetch('https://panel.example.com:2053/panel/api/inbounds/list', {
 method: 'GET',
 headers: { 'Authorization': 'Bearer <token>' },
});`

## Browse by area

### Authentication

### Inbounds

### Clients

### Server

### Settings

### Xray Settings

This reference is regenerated from `public/openapi.json` with `pnpm gen:api`.
Don't edit the generated tag pages by hand.


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/nodes
# Nodes
Manage remote 3x-ui panels acting as nodes for a central panel. All endpoints under /panel/api/nodes.

## List every configured node with its connection details, health, and last heartbeat patch.
GET
/panel/api/nodes/list

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/nodes/list"`

`{ "success": true, "obj": [ { "activeCount": 20, "address": "node.example.com", "allowPrivateAddress": false, "basePath": "/", "clientCount": 25, "configDirty": false, "configDirtyAt": 0, "cpuPct": 12.5, "createdAt": 1700000000, "depletedCount": 1, "disabledCount": 2, "enable": true, "guid": "node-guid", "hasApiToken": true, "id": 1, "inboundCount": 3, "inboundSyncMode": "all", "inboundTags": [ "in-443-tcp" ], "lastError": "", "lastHeartbeat": 1700000000, "latencyMs": 42, "memPct": 45.2, "name": "edge-1", "netDown": 1048576, "netUp": 2097152, "onlineCount": 5, "outboundTag": "direct", "panelVersion": "v3.x.x", "parentGuid": "", "pinnedCertSha256": "", "port": 2053, "remark": "Primary edge", "scheme": "https", "status": "online", "tlsVerifyMode": "verify", "transitive": false, "updatedAt": 1700003600, "uptimeSecs": 86400, "xrayError": "", "xrayState": "running", "xrayVersion": "25.10.31" } ]}`

## This panel's node-auth CA certificate (public, PEM) to paste into a node's mTLS trust setting. Lazily mints the CA and the master client cert on first call. Pair with setting tlsVerifyMode=mtls on the node.
POST
/panel/api/nodes/mtls/ca

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/mtls/ca"`

`{ "success": true, "obj": { "caCert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n" }}`

## Set the CA certificate this panel trusts for incoming node-API client certificates (this panel acting as a node). Paste the managing panel's CA (from nodes/mtls/ca). An empty caCert disables it. A non-empty value must be a PEM certificate. Applied on the next panel restart.
POST
/panel/api/nodes/mtls/trustCA

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/mtls/trustCA" \ -H "Content-Type: application/json" \ -d '{ "caCert": "-----BEGIN CERTIFICATE-----\\n...\\n-----END CERTIFICATE-----\\n" }'`

`{ "success": true, "msg": "string", "obj": null}`

## Validate the stored master mTLS client credential and invalidate cached transports. Each transport closes its old idle pool and rebuilds with the rotated certificate before its next request.
POST
/panel/api/nodes/mtls/reloadClient

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/mtls/reloadClient"`

`{ "success": true, "msg": "string", "obj": null}`

## Fetch a single node by ID.
GET
/panel/api/nodes/get/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

NodeView is the browser/API read contract for nodes. Credentials are
write-only: responses expose only whether a node has a token configured.

`curl -X GET "https://example.com/panel/api/nodes/get/0"`

`{ "success": true, "obj": { "activeCount": 20, "address": "node.example.com", "allowPrivateAddress": false, "basePath": "/", "clientCount": 25, "configDirty": false, "configDirtyAt": 0, "cpuPct": 12.5, "createdAt": 1700000000, "depletedCount": 1, "disabledCount": 2, "enable": true, "guid": "node-guid", "hasApiToken": true, "id": 1, "inboundCount": 3, "inboundSyncMode": "all", "inboundTags": [ "in-443-tcp" ], "lastError": "", "lastHeartbeat": 1700000000, "latencyMs": 42, "memPct": 45.2, "name": "edge-1", "netDown": 1048576, "netUp": 2097152, "onlineCount": 5, "outboundTag": "direct", "panelVersion": "v3.x.x", "parentGuid": "", "pinnedCertSha256": "", "port": 2053, "remark": "Primary edge", "scheme": "https", "status": "online", "tlsVerifyMode": "verify", "transitive": false, "updatedAt": 1700003600, "uptimeSecs": 86400, "xrayError": "", "xrayState": "running", "xrayVersion": "25.10.31" }}`

## Fetch a node's own web TLS certificate/key file paths (proxied to the node). Used by the inbound form's "Set Cert from Panel" so a node-assigned inbound gets paths that exist on the node, not the central panel.
GET
/panel/api/nodes/webCert/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/nodes/webCert/0"`

`{ "success": true, "obj": { "webCertFile": "/root/cert/example.com/fullchain.pem", "webKeyFile": "/root/cert/example.com/privkey.pem" }}`

## Register a new remote node. Provide its URL, write-only apiToken, and optional remark / allowPrivateAddress flag. Responses expose hasApiToken only.
POST
/panel/api/nodes/add

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

NodeView is the browser/API read contract for nodes. Credentials are
write-only: responses expose only whether a node has a token configured.

`curl -X POST "https://example.com/panel/api/nodes/add" \ -H "Content-Type: application/json" \ -d '{ "name": "de-fra-1", "remark": "", "scheme": "https", "address": "node1.example.com", "port": 2053, "basePath": "/", "apiToken": "abcdef...", "clearApiToken": false, "enable": true, "allowPrivateAddress": false }'`

`{ "success": true, "obj": { "activeCount": 20, "address": "node.example.com", "allowPrivateAddress": false, "basePath": "/", "clientCount": 25, "configDirty": false, "configDirtyAt": 0, "cpuPct": 12.5, "createdAt": 1700000000, "depletedCount": 1, "disabledCount": 2, "enable": true, "guid": "node-guid", "hasApiToken": true, "id": 1, "inboundCount": 3, "inboundSyncMode": "all", "inboundTags": [ "in-443-tcp" ], "lastError": "", "lastHeartbeat": 1700000000, "latencyMs": 42, "memPct": 45.2, "name": "edge-1", "netDown": 1048576, "netUp": 2097152, "onlineCount": 5, "outboundTag": "direct", "panelVersion": "v3.x.x", "parentGuid": "", "pinnedCertSha256": "", "port": 2053, "remark": "Primary edge", "scheme": "https", "status": "online", "tlsVerifyMode": "verify", "transitive": false, "updatedAt": 1700003600, "uptimeSecs": 86400, "xrayError": "", "xrayState": "running", "xrayVersion": "25.10.31" }}`

## Replace a node’s connection details. apiToken is write-only: omit it or send an empty string to keep the stored token; set clearApiToken=true to clear it.
POST
/panel/api/nodes/update/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/update/0" \ -H "Content-Type: application/json" \ -d '{ "name": "de-fra-1", "remark": "", "scheme": "https", "address": "node1.example.com", "port": 2053, "basePath": "/", "apiToken": "", "clearApiToken": false, "enable": true, "allowPrivateAddress": false }'`

`{ "success": true, "msg": "string", "obj": null}`

## Delete a node. Inbounds bound to it are not auto-migrated.
POST
/panel/api/nodes/del/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/del/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Pause or resume traffic sync with this node.
POST
/panel/api/nodes/setEnable/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/setEnable/0" \ -H "Content-Type: application/json" \ -d '{ "enable": true }'`

`{ "success": true, "msg": "string", "obj": null}`

## Probe a node without saving it. Uses the body as connection details and returns the same heartbeat snapshot a registered node would have.
POST
/panel/api/nodes/test

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X POST "https://example.com/panel/api/nodes/test" \ -H "Content-Type: application/json" \ -d '{ "scheme": "https", "address": "node1.example.com", "port": 2053, "basePath": "/", "apiToken": "abcdef..." }'`

`{ "success": true, "obj": { "cpuPct": 12.5, "error": "", "latencyMs": 42, "memPct": 45.2, "panelVersion": "v3.x.x", "status": "online", "uptimeSecs": 86400, "xrayError": "", "xrayState": "", "xrayVersion": "25.10.31" }}`

## Connect to the node over HTTPS without verifying its certificate and return the leaf certificate's SHA-256 (base64). Used by the Add/Edit Node dialog to fetch and pin a self-signed certificate. Uses the same body as /test.
POST
/panel/api/nodes/certFingerprint

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/certFingerprint" \ -H "Content-Type: application/json" \ -d '{ "scheme": "https", "address": "node1.example.com", "port": 2053, "basePath": "/" }'`

`{ "success": true, "obj": "k3b1...base64-sha256...="}`

## Use unsaved node connection details to list the remote inbounds available for selective import.
POST
/panel/api/nodes/inbounds

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/inbounds" \ -H "Content-Type: application/json" \ -d '{ "name": "de-fra-1", "scheme": "https", "address": "node1.example.com", "port": 2053, "basePath": "/", "apiToken": "abcdef..." }'`

`{ "success": true, "obj": [ { "tag": "inbound-443", "remark": "VLESS", "protocol": "vless", "port": 443 } ]}`

## Probe an existing node, updating its cached health state.
POST
/panel/api/nodes/probe/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/probe/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Trigger the official panel self-updater on each given node (downloads the latest release and restarts). Only enabled, online nodes are updated; offline/disabled ones are reported as skipped. Set "dev": true to move the nodes to the rolling per-commit dev channel instead of the latest stable release. Returns a per-node result list.
POST
/panel/api/nodes/updatePanel

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/nodes/updatePanel" \ -H "Content-Type: application/json" \ -d '{ "ids": [ 1, 2, 3 ], "dev": false }'`

`{ "success": true, "obj": [ { "id": 1, "name": "de-1", "ok": true }, { "id": 2, "name": "fr-1", "ok": false, "error": "node is offline" } ]}`

## Aggregated metric history for a node — same shape as /server/history, scoped to one node.
GET
/panel/api/nodes/history/{id}/{metric}/{bucket}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Node ID.

`metric*`string

cpu | mem.

`bucket*`integer

Bucket size in seconds. Allowed: 2, 30, 60, 120, 180, 300.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/nodes/history/0/string/0"`

`{ "success": true, "msg": "string", "obj": null}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/server
# Server
System status, log retrieval, certificate generators, Xray binary management, and backup/restore. All under /panel/api/server.

## Serve this API description as an OpenAPI 3 document — the same file that powers the API Docs page. Requires a session or Bearer token like the rest of /panel/api. Useful for generating clients or importing into API tooling.
GET
/panel/api/openapi.json

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/openapi.json"`

`{ "success": true, "msg": "string", "obj": null}`

## Real-time machine snapshot: CPU, memory, swap, disk, network IO, load averages, open connections, Xray state. Cached and refreshed every 2 seconds in the background.
GET
/panel/api/server/status

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/status"`

`{ "success": true, "obj": { "cpu": 12.5, "mem": { "current": 2147483648, "total": 8589934592 }, "swap": { "current": 0, "total": 4294967296 }, "disk": { "current": 53687091200, "total": 268435456000 }, "netIO": { "up": 1073741824, "down": 2147483648 }, "xray": { "state": "running", "version": "v25.10.31" }, "tcpCount": 42, "load": { "load1": 0.5, "load5": 0.3, "load15": 0.2 } }}`

## Reports whether per-client IP limits can be enforced on this host. The panel uses it to gate the "IP Limit" field, since enforcement depends on Fail2ban being installed.
GET
/panel/api/server/fail2banStatus

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/fail2banStatus"`

`{ "success": true, "obj": { "enabled": true, "installed": true, "usable": true, "windows": false }}`

## Legacy: aggregated CPU history. Use /history/cpu/:bucket instead — same data with a uniform {t, v} shape.
GET
/panel/api/server/cpuHistory/{bucket}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`bucket*`integer

Bucket size in seconds. Allowed: 2, 30, 60, 120, 180, 300.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/cpuHistory/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Aggregated time-series for one metric. Returns an array of {t, v} samples covering the last ~6 hours.
GET
/panel/api/server/history/{metric}/{bucket}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`metric*`string

cpu | mem | netUp | netDown | online | load1 | load5 | load15.

`bucket*`integer

Bucket size in seconds. Allowed: 2, 30, 60, 120, 180, 300.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/history/string/0"`

`{ "success": true, "obj": [ { "t": 1700000000, "v": 12.5 }, { "t": 1700000002, "v": 13.1 } ]}`

## Xray runtime metrics state — whether the xray config has a `metrics` block, which expvar keys are flowing, and the current snapshot values for each. Returns an empty state when metrics are not configured.
GET
/panel/api/server/xrayMetricsState

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/xrayMetricsState"`

`{ "success": true, "msg": "string", "obj": null}`

## Time-series history for one Xray runtime metric over the last ~6 hours. Same {t, v} shape as /history/:metric/:bucket.
GET
/panel/api/server/xrayMetricsHistory/{metric}/{bucket}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`metric*`string

xrAlloc | xrSys | xrHeapObjects | xrNumGC | xrPauseNs.

`bucket*`integer

Bucket size in seconds. Allowed: 2, 30, 60, 120, 180, 300.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/xrayMetricsHistory/string/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Latest snapshot from the Xray observatory — per-outbound latency, health status, and last-probe time. Only populated when the Xray config has an observatory configured.
GET
/panel/api/server/xrayObservatory

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/xrayObservatory"`

`{ "success": true, "msg": "string", "obj": null}`

## Time-series of observatory probe results for one outbound tag. Same {t, v} shape as the other history endpoints.
GET
/panel/api/server/xrayObservatoryHistory/{tag}/{bucket}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`tag*`string

Outbound tag from the observatory config.

`bucket*`integer

Bucket size in seconds. Allowed: 2, 30, 60, 120, 180, 300.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/xrayObservatoryHistory/string/0"`

`{ "success": true, "msg": "string", "obj": null}`

## List Xray binary versions available for install on this host.
GET
/panel/api/server/getXrayVersion

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getXrayVersion"`

`{ "success": true, "obj": [ "v25.10.31", "v25.9.15", "v25.8.1" ]}`

## Check whether a newer 3x-ui release is available on GitHub.
GET
/panel/api/server/getPanelUpdateInfo

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getPanelUpdateInfo"`

`{ "success": true, "msg": "string", "obj": null}`

## Report the outcome of the most recently launched panel self-update (see POST updatePanel). Compare the returned runId against the one updatePanel returned to tell this run apart from a stale result.
GET
/panel/api/server/getUpdateStatus

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

PanelUpdateStatus reports the outcome of the most recently launched panel
self-update. RunID lets the caller confirm this status belongs to the
update it started rather than a stale result left over from an earlier
run; State is one of "pending", "success", or "failed". RunID is a decimal
string, not a JSON number: it's a formatted UnixNano timestamp, and
JavaScript's number type can't represent that precisely (it exceeds
Number.MAX_SAFE_INTEGER), which would let two different runs round to the
same value on the wire and defeat the whole point of this field.

`curl -X GET "https://example.com/panel/api/server/getUpdateStatus"`

`{ "success": true, "obj": { "exitCode": 0, "finishedAt": 1735689612, "runId": "1735689600123456789", "state": "success" }}`

## Return the assembled Xray config that’s currently running on this host.
GET
/panel/api/server/getConfigJson

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getConfigJson"`

`{ "success": true, "msg": "string", "obj": null}`

## Stream a full database backup as an attachment: the SQLite .db file on SQLite panels, or a pg_dump custom-format archive (.dump) on PostgreSQL panels. Use as a manual backup.
GET
/panel/api/server/getDb

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getDb"`

`{ "success": true, "msg": "string", "obj": null}`

## Stream a cross-engine migration file as an attachment: a .dump (SQL text) on SQLite, or a .db SQLite database built from the live data on PostgreSQL.
GET
/panel/api/server/getMigration

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getMigration"`

`{ "success": true, "msg": "string", "obj": null}`

## Generate a fresh UUID v4. Convenience helper for client IDs.
GET
/panel/api/server/getNewUUID

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X GET "https://example.com/panel/api/server/getNewUUID"`

`{ "success": true, "obj": { "uuid": "550e8400-e29b-41d4-a716-446655440000" }}`

## Return this panel's own web TLS certificate and key file paths. The central panel calls it on a node (via the node API token) so "Set Cert from Panel" fills a node-assigned inbound with paths that exist on the node.
GET
/panel/api/server/getWebCertFiles

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getWebCertFiles"`

`{ "success": true, "obj": { "webCertFile": "/root/cert/example.com/fullchain.pem", "webKeyFile": "/root/cert/example.com/privkey.pem" }}`

## Read-only summaries (guid, parentGuid, name, address, status, versions) of the nodes this panel manages. A parent panel calls it on a node (via the node API token) to surface transitive sub-nodes in a chained topology. Counts are computed by the parent, not returned here.
GET
/panel/api/server/descendants

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/descendants"`

`{ "success": true, "obj": [ { "guid": "c3d4-...", "parentGuid": "a1b2-...", "name": "Node3", "address": "10.0.0.3", "status": "online" } ]}`

## Generate a new X25519 keypair for Reality.
GET
/panel/api/server/getNewX25519Cert

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getNewX25519Cert"`

`{ "success": true, "obj": { "privateKey": "uN9qLfV3zH8w...", "publicKey": "5v8xPqR2sM7k..." }}`

## Generate a new ML-DSA-65 keypair. Returns {seed, verify}.
GET
/panel/api/server/getNewmldsa65

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X GET "https://example.com/panel/api/server/getNewmldsa65"`

`{ "success": true, "obj": { "seed": "mldsa65-seed", "verify": "mldsa65-verify" }}`

## Generate a new ML-KEM-768 keypair. Returns {seed, client}.
GET
/panel/api/server/getNewmlkem768

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X GET "https://example.com/panel/api/server/getNewmlkem768"`

`{ "success": true, "obj": { "client": "mlkem768-client", "seed": "mlkem768-seed" }}`

## Generate VLESS encryption auth options. Returns an auths array each with id, label, encryption, and decryption fields.
GET
/panel/api/server/getNewVlessEnc

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/server/getNewVlessEnc"`

`{ "success": true, "obj": { "auths": [ { "id": 0, "label": "Auth #0", "encryption": "aes-256-gcm", "decryption": "" } ] }}`

## Stop the Xray binary. All proxies go offline immediately.
POST
/panel/api/server/stopXrayService

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/stopXrayService"`

`{ "success": true, "msg": "string", "obj": null}`

## Reload Xray with the current config. Typically required after structural inbound or routing changes.
POST
/panel/api/server/restartXrayService

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/restartXrayService"`

`{ "success": true, "msg": "string", "obj": null}`

## Download and install the specified Xray version. Pass "latest" for the newest release.
POST
/panel/api/server/installXray/{version}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`version*`string

Xray tag (e.g. v25.10.31) or "latest".

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/installXray/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Self-update the panel to the latest version. The server restarts on success.
POST
/panel/api/server/updatePanel

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`dev?`boolean

Override this run's channel. Omit to use the panel's configured channel.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/updatePanel" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "obj": { "runId": "1735689600123456789" }}`

## Toggle the panel update channel between stable and the rolling per-commit dev release. Only effective on dev builds.
POST
/panel/api/server/setUpdateChannel

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`dev*`boolean

true = dev channel, false = stable.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/setUpdateChannel" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'dev=true'`

`{ "success": true, "msg": "string", "obj": null}`

## Refresh the default GeoIP / GeoSite data files. Use the /:fileName variant to update one file.
POST
/panel/api/server/updateGeofile

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/updateGeofile"`

`{ "success": true, "msg": "string", "obj": null}`

## Refresh a single Geo file by filename (e.g. geoip.dat, geosite.dat).
POST
/panel/api/server/updateGeofile/{fileName}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`fileName*`string

Filename of the data file to refresh.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/updateGeofile/string"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the last N lines of the panel’s own log.
POST
/panel/api/server/logs/{count}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`count*`integer

Number of trailing log lines.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`level?`string

Minimum log level filter.

`syslog?`boolean

Read system logs instead of the panel log.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<string>|null

`curl -X POST "https://example.com/panel/api/server/logs/0" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "obj": [ "2025/01/01 12:00:00 [INFO] Server started", "2025/01/01 12:00:01 [INFO] Xray is running" ]}`

## Return the last N lines of the Xray process log.
POST
/panel/api/server/xraylogs/{count}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`count*`integer

Number of trailing log lines.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`filter?`string

Keyword filter — only lines containing this string.

`showDirect?`string

"true" to include direct (freedom) traffic lines.

`showBlocked?`string

"true" to include blocked (blackhole) traffic lines.

`showProxy?`string

"true" to include proxy traffic lines.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>|null

`curl -X POST "https://example.com/panel/api/server/xraylogs/0" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "obj": [ { "DateTime": "2025-01-01T12:00:00Z", "Email": "alice@example.com", "Event": 0, "FromAddress": "192.0.2.10:54321", "Inbound": "inbound-443", "Outbound": "direct", "ToAddress": "example.com:443" } ]}`

## Return live AmneziaWG peer activity (handshake, endpoint, transfer) plus the panel’s own AmneziaWG event lines.
POST
/panel/api/server/amneziawglogs/{count}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`count*`integer

Maximum peer rows and event lines to return.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`filter?`string

Keyword filter — only rows/lines containing this string.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

AmneziaWGLogs is what the overview's AmneziaWG log view renders: the live
per-peer activity of every running embedded interface, plus the panel's
own recent AmneziaWG lifecycle log lines that explain a peer being absent
from Peers at all.

`curl -X POST "https://example.com/panel/api/server/amneziawglogs/0" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "obj": { "events": [ "2025/01/01 12:00:00 amneziawg: started interface awg1 for inbound 1" ], "peers": [ { "allowedIPs": "10.8.1.2/32", "down": 4194304, "email": "peer@example.com", "endpoint": "203.0.113.9:51820", "handshake": 1735732800000, "inboundId": 1, "interface": "awg1", "online": true, "tag": "inbound-51820", "up": 1048576 } ], "running": true }}`

## Restore the panel DB from an uploaded backup (multipart form, field name "db"). SQLite panels accept a SQLite database (.db) or a SQLite migration dump (.dump); PostgreSQL panels accept a pg_dump archive (.dump), a SQLite database (.db), or a SQLite migration dump. The panel restarts after restore. Destructive.
POST
/panel/api/server/importDB

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`multipart/form-data`

- body

- body
- …

`db*`unknown

Database backup or migration file to upload.

`keepHostSettings?`boolean

Keep this machine's addresses, certificates and node identity. Default true.

Default`true`

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/importDB" \ -F db="null"`

`{ "success": true, "msg": "string", "obj": null}`

## Generate a new ECH (Encrypted Client Hello) keypair and config list for the given SNI.
POST
/panel/api/server/getNewEchCert

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`sni*`string

Server Name Indication to generate the ECH config for.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/getNewEchCert" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'sni=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Compute the hex SHA-256 of a certificate (DER) for pinning (pinnedPeerCertSha256). Provide either a server file path or inline PEM/DER content.
POST
/panel/api/server/getCertHash

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`certFile*`string

Path to a certificate file on the server. Takes precedence over certContent.

Match`.*\S.*`

`certContent?`string

Inline PEM (or DER) certificate content, used when certFile is empty.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/getCertHash" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'certFile=string'`

`{ "success": true, "obj": [ "e8e2d3..." ]}`

## Run `xray tls ping` against a remote server and return its live leaf-certificate SHA-256 hash(es) for pinning (pinnedPeerCertSha256).
POST
/panel/api/server/getRemoteCertHash

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`server*`string

Remote server as domain or domain:port (default port 443), e.g. cloudflare-dns.com.

`allowPrivate?`boolean

Ping a private/internal/loopback server (LAN, Docker service name). Default false (SSRF guard blocks it and the error response sets obj.privateTarget=true).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/getRemoteCertHash" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'server=string'`

`{ "success": true, "obj": [ "e8e2d3..." ]}`

## Run a live TLS 1.3 probe against a candidate REALITY target and return a feasibility verdict (TLS 1.3 + h2 + X25519 + trusted certificate) plus the certificate SAN DNS names. A target on a private/loopback address is reported with privateTarget=true and probed only when allowPrivate is set.
POST
/panel/api/server/scanRealityTarget

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`target*`string

Candidate target as host or host:port (default port 443), e.g. www.cloudflare.com:443.

`sni?`string

SNI the handshake sends and the certificate is verified against (the inbound serverNames). Defaults to the target host, which a fronting proxy answers with its default certificate.

`xver?`integer

PROXY protocol version the target expects (matches the inbound xver). 0 = none.

`allowPrivate?`boolean

Probe a private/internal/loopback target (LAN, Docker service name). Default false (SSRF guard blocks it and the response sets privateTarget=true).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

`curl -X POST "https://example.com/panel/api/server/scanRealityTarget" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'target=string'`

`{ "success": true, "obj": { "alpn": "h2", "certChainBytes": 3427, "certChainValid": true, "certIssuer": "Google Trust Services", "certSubject": "cloudflare.com", "certValid": true, "curveID": "X25519", "feasible": true, "h2": true, "host": "www.cloudflare.com", "ip": "104.16.124.96", "latencyMs": 180, "notAfter": "2026-08-01T00:00:00Z", "port": 443, "privateTarget": false, "reason": "", "serverNames": [ "" ], "target": "www.cloudflare.com:443", "tls13": true, "tlsVersion": "1.3", "x25519": true }}`

## Probe/discover REALITY targets and return each verdict ranked by feasibility then latency. Each comma-separated token may be a domain (validated with SNI), a bare IP, or a CIDR range (discovered without SNI by reading the certificate domain). When empty, the realityScanCandidates setting is probed (the built-in seed list if that setting is empty).
POST
/panel/api/server/scanRealityTargets

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`targets?`string

Optional comma-separated tokens: domain[:port], IP[:port], or CIDR (e.g. 104.16.0.0/24). When omitted, the realityScanCandidates setting is probed (the built-in seed list if that setting is empty).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X POST "https://example.com/panel/api/server/scanRealityTargets" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "obj": [ { "alpn": "h2", "certChainBytes": 3427, "certChainValid": true, "certIssuer": "Google Trust Services", "certSubject": "cloudflare.com", "certValid": true, "curveID": "X25519", "feasible": true, "h2": true, "host": "www.cloudflare.com", "ip": "104.16.124.96", "latencyMs": 180, "notAfter": "2026-08-01T00:00:00Z", "port": 443, "privateTarget": false, "reason": "", "serverNames": [ "" ], "target": "www.cloudflare.com:443", "tls13": true, "tlsVersion": "1.3", "x25519": true } ]}`

## Fetch the fully aggregated inbound_client_ips database table. Used by nodes to sync recently active IPs across the cluster.
GET
/panel/api/server/clientIps

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/server/clientIps"`

`{ "success": true, "obj": [ { "clientEmail": "", "id": 0, "ips": null } ]}`

## Submit a list of recently active IP timestamps. The panel merges them with the existing database to maintain a unified global IP-limit view.
POST
/panel/api/server/clientIps

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`[index: integer]?`

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/server/clientIps" \ -H "Content-Type: application/json" \ -d '[ { "clientEmail": "string", "ips": [ { "ip": "string", "timestamp": 0 } ] } ]'`

`{ "success": true, "msg": "string", "obj": null}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/settings
# Settings
Panel configuration and user credentials. All endpoints live under /panel/api/setting and require a logged-in session or Bearer token.

## Return every panel setting: web server, Telegram bot, subscription, security, LDAP. The full JSON blob that the Settings page edits.
POST
/panel/api/setting/all

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/all"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the computed default settings based on the request host. Useful to preview what a fresh install would use.
POST
/panel/api/setting/defaultSettings

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/defaultSettings"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the shipped (factory) default value per browser-safe setting key, so clients can tell a stored value apart from the default it would fall back to. Per-install material (secret, panelGuid, mTLS keys) and credential fields are never included.
POST
/panel/api/setting/factoryDefaults

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/factoryDefaults"`

`{ "success": true, "msg": "string", "obj": null}`

## Persist every setting at once. The body mirrors the shape returned by /all. Invalid values (bad ports, missing cert pairs, etc.) are rejected before write.
POST
/panel/api/setting/update

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/update" \ -H "Content-Type: application/json" \ -d '{}'`

`{ "success": true, "msg": "string", "obj": null}`

## Validate any regular expression with the backend Go RE2 compiler without saving it.
POST
/panel/api/setting/validateRegex

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/validateRegex" \ -H "Content-Type: application/json" \ -d '{ "regex": "(?m)^general-purpose$" }'`

`{ "success": true, "msg": ""}`

## Change the panel admin username and password. Requires the current credentials for verification. The session is refreshed with the new values on success.
POST
/panel/api/setting/updateUser

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/json`

- body

- body
- …

`oldUsername*`string

Current admin username.

`oldPassword*`string

Current admin password.

`newUsername*`string

Desired new username.

`newPassword*`string

Desired new password.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/updateUser" \ -H "Content-Type: application/json" \ -d '{ "oldUsername": "admin", "oldPassword": "admin", "newUsername": "newadmin", "newPassword": "newpass" }'`

`{ "success": true, "msg": "string", "obj": null}`

## Restart the entire 3x-ui process after a 3-second grace period. The connection drops immediately; the panel comes back online ~5-10 seconds later.
POST
/panel/api/setting/restartPanel

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/restartPanel"`

`{ "success": true, "msg": "string", "obj": null}`

## Test SMTP connection with stage-by-stage reporting (connect, auth, send). Returns structured result with stage and message.
POST
/panel/api/setting/testSmtp

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/testSmtp"`

`{ "success": true, "stage": "send", "msg": "Test email sent successfully"}`

## Test Telegram bot connection by sending a test message to the configured chat.
POST
/panel/api/setting/testTgBot

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/testTgBot"`

`{ "success": true, "msg": "Test message sent to Telegram"}`

## Test Discord bot connection by sending a test embed to the configured channel.
POST
/panel/api/setting/testDiscord

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/setting/testDiscord"`

`{ "success": true, "msg": "Test notification sent successfully"}`

## Return the built-in default Xray JSON config template that ships with this panel version.
GET
/panel/api/setting/getDefaultJsonConfig

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/setting/getDefaultJsonConfig"`

`{ "success": true, "msg": "string", "obj": null}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/subscription-balancers
# Subscription Balancers
Client-side balancers for the JSON subscription: each enabled balancer is emitted as one extra config document whose members are the proxy outbounds of the selected inbounds (routing.balancers + burstObservatory). Managed in Settings → Sub Balancers.

## List all subscription balancers in sort order (sort_order asc, id asc).
GET
/panel/api/sub-balancers

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`array<>

`curl -X GET "https://example.com/panel/api/sub-balancers"`

`{ "success": true, "obj": [ { "createdAt": 1710000000000, "enabled": true, "id": 1, "inboundIds": [ 1, 3 ], "memberWeights": {}, "remark": "auto-fastest", "sortOrder": 1, "strategy": "random", "updatedAt": 1710000000000 } ]}`

## Create a subscription balancer. It appears in the JSON subscription of every client that sits on at least one selected inbound.
POST
/panel/api/sub-balancers

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`remark*`string

Display label, used as the config remarks (required).

`strategy?`string

Balancer strategy: "leastLoad", "leastPing", "roundRobin" or "random". Default "random".

Default`"random"`

`inboundIds*`array<integer>

Repeated form keys selecting the member inbounds (required, at least one).

`memberWeights?`

leastLoad only: JSON object mapping inbound id to a static weight > 0, e.g. {"3":0.2}. Lower weight = picked more often; absent ids weigh 1. Rejected for other strategies; entries for unselected inbounds are dropped.

`sortOrder?`integer

1-based position in the subscription list. Default 1.

Default`1`

`enabled?`boolean

Whether the balancer is emitted. Default true on create; unchanged when omitted on update.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

SubBalancer is one extra JSON-subscription config document whose members are
the selected inbounds' proxy outbounds. SortOrder shares SubSortIndex semantics.

`curl -X POST "https://example.com/panel/api/sub-balancers" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'remark=string&inboundIds=0'`

`{ "success": true, "obj": { "createdAt": 1710000000000, "enabled": true, "id": 1, "inboundIds": [ 1, 3 ], "memberWeights": {}, "remark": "auto-fastest", "sortOrder": 1, "strategy": "random", "updatedAt": 1710000000000 }}`

## Update a balancer by id. Accepts the same form fields as create (full-row update); omitting memberWeights clears stored weights, while omitting enabled keeps its current value.
POST
/panel/api/sub-balancers/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Balancer id.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`remark*`string

Display label, used as the config remarks (required).

`strategy?`string

Balancer strategy: "leastLoad", "leastPing", "roundRobin" or "random". Default "random".

Default`"random"`

`inboundIds*`array<integer>

Repeated form keys selecting the member inbounds (required, at least one).

`memberWeights?`

leastLoad only: JSON object mapping inbound id to a static weight > 0, e.g. {"3":0.2}. Lower weight = picked more often; absent ids weigh 1. Rejected for other strategies; entries for unselected inbounds are dropped.

`sortOrder?`integer

1-based position in the subscription list. Default 1.

Default`1`

`enabled?`boolean

Whether the balancer is emitted. Default true on create; unchanged when omitted on update.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

SubBalancer is one extra JSON-subscription config document whose members are
the selected inbounds' proxy outbounds. SortOrder shares SubSortIndex semantics.

`curl -X POST "https://example.com/panel/api/sub-balancers/0" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'remark=string&inboundIds=0'`

`{ "success": true, "obj": { "createdAt": 1710000000000, "enabled": true, "id": 1, "inboundIds": [ 1, 3 ], "memberWeights": {}, "remark": "auto-fastest", "sortOrder": 1, "strategy": "random", "updatedAt": 1710000000000 }}`

## Delete a balancer by id.
DELETE
/panel/api/sub-balancers/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Balancer id.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

SubBalancer is one extra JSON-subscription config document whose members are
the selected inbounds' proxy outbounds. SortOrder shares SubSortIndex semantics.

`curl -X DELETE "https://example.com/panel/api/sub-balancers/0"`

`{ "success": true, "obj": { "createdAt": 1710000000000, "enabled": true, "id": 1, "inboundIds": [ 1, 3 ], "memberWeights": {}, "remark": "auto-fastest", "sortOrder": 1, "strategy": "random", "updatedAt": 1710000000000 }}`

## Delete a balancer by id (POST alias of DELETE for clients that cannot send DELETE).
POST
/panel/api/sub-balancers/{id}/del

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Balancer id.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`

SubBalancer is one extra JSON-subscription config document whose members are
the selected inbounds' proxy outbounds. SortOrder shares SubSortIndex semantics.

`curl -X POST "https://example.com/panel/api/sub-balancers/0/del"`

`{ "success": true, "obj": { "createdAt": 1710000000000, "enabled": true, "id": 1, "inboundIds": [ 1, 3 ], "memberWeights": {}, "remark": "auto-fastest", "sortOrder": 1, "strategy": "random", "updatedAt": 1710000000000 }}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/subscription-server
# Subscription Server
A separate HTTP/HTTPS server that serves proxy subscription links (standard, JSON, and Clash) to clients. The server listens on its own port (default 2096) and is configured in Settings → Subscription. Fresh panels generate random path prefixes for each format; all paths remain configurable. Every subscription endpoint sets response headers for client apps to read traffic/expiry info.

## Return base64-encoded subscription links for all enabled clients matching the subscription ID. When the request has an Accept: text/html header or ?html=1, renders a styled info page instead. With ?format=info, returns the page view-model as JSON (traffic, expiry, online status; no links) for live polling. The path prefix is configured by subPath.
GET
/{subPath}{subid}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`subPath*`string

### Query Parameters

`format?`string

Set to "info" to get the subscription status view-model as JSON instead of the links.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/stringstring"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the same status and subscription metadata headers as GET without a response body.
HEAD
/{subPath}{subid}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`subPath*`string

### Response Body

Subscription is available. Headers match GET; no response body.

`curl -X HEAD "https://example.com/stringstring"`

Empty

## Return aggregate HWID device-slot usage for the subscription: whether an HWID limit is active, the limit, how many devices are registered and how many slots remain. Read-only — it never registers a device, so asking does not consume a slot. Counters only: no HWID value, email or device metadata. The path prefix is configured by subPath.
GET
/{subPath}{subid}/hwid-status

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`subPath*`string

### Response Body

Device-slot counters for the subscription.

`application/json`

- response

- response
- …

HwidSlotStatus is the aggregate device-slot view exposed to subscribers:
counters only, no hwid value or hash, no email, no device metadata.

`active*`boolean

`full*`boolean

`limit*`integer

`registered*`integer

`remaining*`integer

`curl -X GET "https://example.com/stringstring/hwid-status"`

`{ "active": true, "full": false, "limit": 2, "registered": 1, "remaining": 1}`

## Return the HWID device-slot status code and headers as GET without a response body.
HEAD
/{subPath}{subid}/hwid-status

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`subPath*`string

### Response Body

Headers match GET; no response body.

`curl -X HEAD "https://example.com/stringstring/hwid-status"`

Empty

## Return subscription as a JSON array of proxy configs (one per enabled client). Only when JSON subscription is enabled in settings. The path prefix is configured by subJsonPath.
GET
/{jsonPath}{subid}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`jsonPath*`string

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/stringstring"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the JSON subscription status and metadata headers without a body. Registered only when JSON subscriptions are enabled.
HEAD
/{jsonPath}{subid}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`jsonPath*`string

### Response Body

Subscription is available. Headers match GET; no response body.

`curl -X HEAD "https://example.com/stringstring"`

Empty

## Return subscription as a Clash/Mihomo-compatible YAML config, including configured global Clash routing rules. Only when Clash subscription is enabled in settings. The path prefix is configured by subClashPath.
GET
/{clashPath}{subid}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`clashPath*`string

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/stringstring"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the Clash subscription status and metadata headers without a body. Registered only when Clash subscriptions are enabled.
HEAD
/{clashPath}{subid}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`subid*`string

Client subscription ID.

`clashPath*`string

### Response Body

Subscription is available. Headers match GET; no response body.

`curl -X HEAD "https://example.com/stringstring"`

Empty


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/websocket
# WebSocket
Real-time status updates via WebSocket. Connect once at <code>ws://<panel>/ws</code> to receive a stream of JSON messages without polling. Requires an authenticated session cookie (Bearer token auth is not supported). Each message has a <code>type</code> field that identifies the payload shape.

## Upgrade an HTTP connection to a WebSocket. Requires an authenticated session cookie (Bearer token auth is not supported here). Returns 101 Switching Protocols on success. The server then pushes JSON messages described below.
GET
/ws

### Authorization

`cookieAuth`

cookie`3x-ui``<token>`

Session cookie set by POST /login. Browser-only.

### Response Body

Switching Protocols. WebSocket messages use WebSocketEnvelope.

`curl -X GET "https://example.com/ws"`

Empty


=== SOURCE: https://docs.sanaei.dev/docs/reference/api/xray-settings
# Xray Settings
Xray configuration template, outbound management, Warp/Nord/PIA integration, and config testing. All endpoints under /panel/api/xray.

## Return the Xray config template (JSON string), available inbound tags, client reverse tags, and the configured outbound test URL in one response.
POST
/panel/api/xray/

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/"`

`{ "success": true, "obj": { "xraySetting": "{...raw xray config...}", "inboundTags": "[\"in-443-tcp\"]", "clientReverseTags": "[]", "outboundTestUrl": "https://www.google.com/generate_204" }}`

## Return the built-in default Xray config shipped with the panel (identical to /panel/api/setting/getDefaultJsonConfig).
GET
/panel/api/xray/getDefaultJsonConfig

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/getDefaultJsonConfig"`

`{ "success": true, "msg": "string", "obj": null}`

## Return traffic statistics for every outbound. Each outbound shows up/down/total counters.
GET
/panel/api/xray/getOutboundsTraffic

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/getOutboundsTraffic"`

`{ "success": true, "msg": "string", "obj": null}`

## Return the most recent Xray process stdout/stderr output. Useful to check for startup errors or runtime warnings.
GET
/panel/api/xray/getXrayResult

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/getXrayResult"`

`{ "success": true, "msg": "string", "obj": null}`

## Save the Xray JSON config template and optionally the outbound test URL. Both are sent as form fields.
POST
/panel/api/xray/update

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`xraySetting*`string

Full Xray JSON config template.

`outboundTestUrl?`string

URL used for outbound reachability tests. Defaults to https://www.google.com/generate_204.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/update" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'xraySetting=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Manage Cloudflare Warp integration. The action parameter selects the operation.
POST
/panel/api/xray/warp/{action}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`action*`string

data — return Warp stats. del — delete Warp data. config — return current config. reg — register (sends keys). changeIp — rotate the endpoint. license — set a Warp+ key. interval — set automatic rotation in hours.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`privateKey?`string

Required when action=reg.

`publicKey?`string

Required when action=reg.

`license?`string

Required when action=license.

`interval?`integer

Non-negative hours between automatic rotations. Required when action=interval; 0 disables rotation.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/warp/string" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "msg": "string", "obj": null}`

## Manage NordVPN integration. The action parameter selects the operation.
POST
/panel/api/xray/nord/{action}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`action*`string

countries — list available countries. servers — list servers in a country (sends countryId). reg — get NordVPN credentials (sends token). setKey — store NordVPN API key (sends key). data — return current NordVPN connection data. del — delete NordVPN data.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`countryId?`string

Required when action=servers.

`token?`string

Required when action=reg.

`key?`string

Required when action=setKey.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/nord/string" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "msg": "string", "obj": null}`

## Manage PIA WireGuard integration. The action parameter selects the operation.
POST
/panel/api/xray/pia/{action}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`action*`string

countries — list available countries from the signed PIA server list. servers — list regions and WireGuard servers in a country (sends countryCode). reg — sign in with a PIA username and password (sends username, password). data — return the signed-in account hint. del — delete stored PIA credentials. addKey — register a WireGuard key with the selected server (sends hostname) and return fields to build the outbound.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`username?`string

Required when action=reg.

`password?`string

Required when action=reg.

`countryCode?`string

Required when action=servers.

`hostname?`string

Required when action=addKey.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/pia/string" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "msg": "string", "obj": null}`

## Reset traffic counters for a specific outbound by tag.
POST
/panel/api/xray/resetOutboundsTraffic

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`tag*`string

Outbound tag to reset (e.g. "proxy", "direct").

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/resetOutboundsTraffic" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'tag=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Test an outbound configuration. Sends the outbound JSON (required), optionally all outbounds (to resolve sockopt.dialerProxy dependencies), and a mode flag.
POST
/panel/api/xray/testOutbound

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`outbound*`string

JSON-encoded single outbound to test (required).

`allOutbounds?`string

JSON array of all outbounds — used to resolve dialerProxy chains.

`mode?`string

"tcp" for a fast dial-only probe (parallel-safe), "real" for a real-delay probe whose delay is the full request time including tunnel establishment. Default/empty uses a full HTTP probe reporting the warm per-request round-trip. Both HTTP variants run through a temp xray instance.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/testOutbound" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'outbound=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Test a batch of outbounds (max 50) through one shared temp xray instance. Returns an array of results in input order, each with the outbound tag, delay, HTTP status and a connect/TLS/TTFB timing breakdown.
POST
/panel/api/xray/testOutbounds

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`outbounds*`string

JSON array of outbound configs to test (required).

`allOutbounds?`string

JSON array of all outbounds — used to resolve dialerProxy chains.

`mode?`string

"tcp" for fast dial-only probes (UDP-transport outbounds are still probed over HTTP), "real" for real-delay probes whose delay is the full request time including tunnel establishment. Default/empty routes an HTTP request through each outbound and reports the warm per-request round-trip.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/testOutbounds" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'outbounds=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Live state of routing balancers in the running core (RoutingService.GetBalancerInfo): current override and the targets the strategy prefers. Returns a map keyed by balancer tag.
POST
/panel/api/xray/balancerStatus

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`tags*`string

Comma-separated balancer tags to query (e.g. "b1,b2").

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/balancerStatus" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'tags=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Force a balancer in the running core to always pick one outbound (RoutingService.OverrideBalancerTarget). Applied live without a restart; cleared automatically when Xray restarts.
POST
/panel/api/xray/balancerOverride

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`tag*`string

Balancer tag (required).

`target?`string

Outbound tag to force. Empty clears the override and returns control to the strategy.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/balancerOverride" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'tag=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Ask the running core which outbound its router would pick for a synthetic connection (RoutingService.TestRoute). No traffic is sent.
POST
/panel/api/xray/routeTest

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`domain*`string

Target domain. Either domain or ip is required.

Length`1 <= length`

`ip?`string

Target IP. Either domain or ip is required.

`port?`integer

Target port (optional).

`network?`string

"tcp" (default) or "udp".

`inboundTag?`string

Simulate arrival on this inbound (optional).

`protocol?`string

Sniffed protocol such as http, tls, bittorrent (optional).

`email?`string

User attribution for user-based rules (optional).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/routeTest" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'domain=string'`

`{ "success": true, "msg": "string", "obj": null}`

## List the geo databases (.dat files) in the Xray asset folder, with the layout detected from their contents, size, modification time and category count. A database that fails to parse is still listed, with the reason in "error".
GET
/panel/api/xray/geodata/files

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/geodata/files"`

`{ "success": true, "msg": "string", "obj": null}`

## One page of a database's categories, each with its entry count and the attributes its domains carry (e.g. "ads", "cn").
GET
/panel/api/xray/geodata/categories

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Query Parameters

`file*`string

Database file name inside the asset folder, e.g. geosite.dat (required).

`q?`string

Case-insensitive substring filter on the category code.

`offset?`integer

Rows to skip. Defaults to 0.

`limit?`integer

Rows to return, capped at 500. Omit it to return every category — the index is small and the panel filters it client-side.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/geodata/categories?file=string"`

`{ "success": true, "msg": "string", "obj": null}`

## One page of the rules inside a category — domain rules typed as domain/full/keyword/regexp for geosite databases, CIDRs for geoip ones.
GET
/panel/api/xray/geodata/entries

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Query Parameters

`file*`string

Database file name inside the asset folder (required).

`code*`string

Category code, case-insensitive, e.g. google (required).

`q?`string

Case-insensitive substring filter on the rule value.

`offset?`integer

Rows to skip. Defaults to 0.

`limit?`integer

Rows to return, capped at 500. Defaults to the cap.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/geodata/entries?file=string&code=string"`

`{ "success": true, "msg": "string", "obj": null}`

## Check routing tokens against the databases on disk and return only the ones that do not resolve. Plain domains and CIDRs are ignored. Each issue carries a reason: syntax, fileMissing or categoryMissing.
POST
/panel/api/xray/geodata/validate

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`tokens*`string

Comma-separated routing tokens, e.g. "geosite:google,geosite:blabla". Max 500 per request.

`kind?`string

"ip" to parse the tokens as IP rules (geoip:, ext-ip:, leading !). Anything else parses them as domain rules (geosite:, ext-site:).

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/geodata/validate" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'tokens=string'`

`{ "success": true, "msg": "string", "obj": null}`

## List all outbound subscriptions (remote URLs that supply additional outbounds), newest first.
GET
/panel/api/xray/outbound-subs

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X GET "https://example.com/panel/api/xray/outbound-subs"`

`{ "success": true, "msg": "string", "obj": null}`

## Create an outbound subscription. The URL is fetched, parsed into outbounds with stable tags, and merged additively into the running Xray config.
POST
/panel/api/xray/outbound-subs

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`remark?`string

Optional display label.

`url*`string

Subscription URL (required). Must be a public http(s) address; private/internal targets are blocked unless allowPrivate is true.

`tagPrefix?`string

Prefix for generated outbound tags. Defaults to the lowest free "sub-" prefix.

`userAgent?`string

Custom User-Agent sent when fetching this subscription. Defaults to "3x-ui-outbound-sub/1.0".

Default`"3x-ui-outbound-sub/1.0"`

`updateInterval?`integer

Seconds between auto-refreshes. Default 600.

Default`600`

`enabled?`boolean

Whether the subscription is active. Default true.

Default`true`

`allowPrivate?`boolean

Allow the URL to point at a private/internal/loopback address. Default false.

Default`false`

`allowInsecure?`boolean

Skip TLS certificate verification when fetching the subscription's URL. Default false.

Default`false`

`prepend?`boolean

Place this subscription's outbounds before the manual template outbounds. Default false.

Default`false`

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/outbound-subs" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'url=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Update an existing outbound subscription by id. Accepts the same form fields as create.
POST
/panel/api/xray/outbound-subs/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Subscription id.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`remark?`string

Optional display label.

`url*`string

Subscription URL (required). Must be a public http(s) address; private/internal targets are blocked unless allowPrivate is true.

`tagPrefix?`string

Prefix for generated outbound tags. Defaults to the lowest free "sub-" prefix.

`userAgent?`string

Custom User-Agent sent when fetching this subscription. Defaults to "3x-ui-outbound-sub/1.0".

Default`"3x-ui-outbound-sub/1.0"`

`updateInterval?`integer

Seconds between auto-refreshes. Default 600.

Default`600`

`enabled?`boolean

Whether the subscription is active. Default true.

Default`true`

`allowPrivate?`boolean

Allow the URL to point at a private/internal/loopback address. Default false.

Default`false`

`allowInsecure?`boolean

Skip TLS certificate verification when fetching the subscription's URL. Default false.

Default`false`

`prepend?`boolean

Place this subscription's outbounds before the manual template outbounds. Default false.

Default`false`

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/outbound-subs/0" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'url=string'`

`{ "success": true, "msg": "string", "obj": null}`

## Delete an outbound subscription by id.
DELETE
/panel/api/xray/outbound-subs/{id}

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Subscription id.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X DELETE "https://example.com/panel/api/xray/outbound-subs/0"`

`{ "success": true, "msg": "string", "obj": null}`

## Delete an outbound subscription by id (POST alias of DELETE for clients that cannot send DELETE).
POST
/panel/api/xray/outbound-subs/{id}/del

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Subscription id.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/outbound-subs/0/del"`

`{ "success": true, "msg": "string", "obj": null}`

## Force an immediate re-fetch of the subscription and return the parsed outbounds. Signals Xray to reload.
POST
/panel/api/xray/outbound-subs/{id}/refresh

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Subscription id.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/outbound-subs/0/refresh"`

`{ "success": true, "msg": "string", "obj": null}`

## Reorder a subscription one step up or down in priority (controls its position in the merged outbounds).
POST
/panel/api/xray/outbound-subs/{id}/move

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Path Parameters

`id*`integer

Subscription id.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`dir?`string

"up" to raise priority, anything else to lower it.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/outbound-subs/0/move" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d ''`

`{ "success": true, "msg": "string", "obj": null}`

## Preview a subscription URL: fetch and parse it into outbounds without persisting anything.
POST
/panel/api/xray/outbound-subs/parse

### Authorization

``

header`Authorization``Bearer <token>`

API token from Settings → Security → API Token. Send as `Authorization: Bearer <token>`.

### Request Body

`application/x-www-form-urlencoded`

- body

- body
- …

`url*`string

Subscription URL to preview (required).

`userAgent?`string

Custom User-Agent sent while fetching the preview.

`allowPrivate?`boolean

Allow a private/internal/loopback URL. Default false.

`allowInsecure?`boolean

Skip TLS certificate verification. Default false.

### Response Body

Successful response

`application/json`

- response

- response
- …

`success?`boolean

`msg?`string

`obj?`unknown

`curl -X POST "https://example.com/panel/api/xray/outbound-subs/parse" \ -H "Content-Type: application/x-www-form-urlencoded" \ -d 'url=string'`

`{ "success": true, "msg": "string", "obj": null}`


=== SOURCE: https://docs.sanaei.dev/docs/reference/database
# Database
3x-ui storage backends — SQLite (default) and PostgreSQL — the database path, connection pool, and SQLite-to-PostgreSQL migration.

3x-ui stores everything — inbounds, clients, settings — in a database. You choose
the backend at install time; both are first-class.

## SQLite (default)

A single file at `/etc/x-ui/x-ui.db`. Zero setup, ideal for small and medium
deployments. The folder is configurable with
`XUI_DB_FOLDER` (on Windows it defaults next
to the binary).

## PostgreSQL

Recommended for high client counts or multi-node setups. The installer can
install PostgreSQL locally for you, or accept a DSN to an existing server. At
runtime the backend is selected via environment variables, which the installer
writes to `/etc/default/x-ui`:

/etc/default/x-ui

`XUI_DB_TYPE=postgres
XUI_DB_DSN=postgres://xui:password@127.0.0.1:5432/xui?sslmode=disable`

Tune the connection pool with `XUI_DB_MAX_OPEN_CONNS` and
`XUI_DB_MAX_IDLE_CONNS`.

### Docker

`docker compose up -d` keeps using SQLite. To run with the bundled PostgreSQL
service, uncomment the two `XUI_DB_*` lines in `docker-compose.yml` and start
with the profile:

`docker compose --profile postgres up -d`

## Migrate SQLite → PostgreSQL

Move an existing SQLite install to PostgreSQL with the built-in command:

`x-ui migrate-db --dsn "postgres://xui:password@127.0.0.1:5432/xui?sslmode=disable"`

Then set `XUI_DB_TYPE` and `XUI_DB_DSN` in `/etc/default/x-ui` and restart:

`systemctl restart x-ui`

The source SQLite file is left untouched — remove it manually only after you've
verified the new backend works.

## Backups

Whichever backend you use, back it up regularly — see
Backup & restore.


=== SOURCE: https://docs.sanaei.dev/docs/reference/env-vars
# Environment Variables
Complete reference for 3x-ui's XUI_* environment variables — database, panel, logging, memory, node token encryption, and the tunnel health monitor.

3x-ui reads its runtime configuration from `XUI_*` environment variables. On a
script install the installer writes them to the service environment file
(`/etc/default/x-ui`, or `/etc/conf.d/x-ui` / `/etc/sysconfig/x-ui` depending on
the distro); for Docker you set them in `docker-compose.yml` or `docker run -e`.
Defaults are sensible — set only what you need to change, then restart:
`systemctl restart x-ui`.

## Database

Variable | Default | Description | 
`XUI_DB_TYPE` | `sqlite` | Backend: `sqlite`, or `postgres` (also accepts `postgresql` / `pg`). | 
`XUI_DB_FOLDER` | `/etc/x-ui` | Folder for the SQLite database file (`x-ui.db`). | 
`XUI_DB_DSN` | — | PostgreSQL connection string (used when `XUI_DB_TYPE=postgres`). | 
`XUI_DB_MAX_OPEN_CONNS` | — | Max open connections in the PostgreSQL pool. | 
`XUI_DB_MAX_IDLE_CONNS` | — | Max idle connections in the PostgreSQL pool. | 

The default SQLite database path is `/etc/x-ui/x-ui.db`. See
Database for the SQLite ↔ PostgreSQL details.

## Panel

Variable | Default | Description | 
`XUI_PORT` | — | Override the panel port (1–65535). Takes precedence over the stored setting. | 
`XUI_INIT_WEB_BASE_PATH` | `/` | Initial web base path on first launch (e.g. `/panel`). | 
`XUI_ENABLE_FAIL2BAN` | `true` | Enable Fail2ban-based IP-limit enforcement. | 
`XUI_SKIP_HSTS` | `false` | Skip the HSTS header — set `true` when TLS is terminated by a reverse proxy. | 

## Node token encryption

Node API bearer tokens — and the stored PIA token — are kept in plaintext by
default. Encryption at rest is opt-in and fails closed: with any mode other than
`off`, the panel refuses to start unless it can load a key.

Variable | Default | Description | 
`NODE_TOKEN_ENCRYPTION` | `off` | `off`, `migration` (reads accept plaintext or ciphertext, writes encrypt), or `required` (same writes, startup fails without a key). Note the missing `XUI_` prefix. | 
`XUI_NODE_TOKEN_KEY_FILE` | `/etc/x-ui/node_token_key.json` | JSON keyring, mode `0600` or stricter (not checked on Windows, where NTFS permissions protect it). Loaded first. | 
`XUI_NODE_TOKEN_KEY` | — | A single base64 32-byte key, read only when the key file fails to load. Its key id is fixed to `env`, so it cannot rotate. | 

The key file names the active key plus every older key still needed to decrypt:

`{ "active": "k1", "keys": { "k1": "<base64 32-byte key>" } }`

Generate a key with `openssl rand -base64 32`; keys are never accepted as
command-line arguments. After enabling a mode, re-encrypt the rows already in
the database under the active key:

`x-ui encrypt-tokens`

That covers node rows; the PIA token is re-encrypted the next time it is read.
To rotate, add the new key to `keys`, point `active` at it, keep the old key for
decryption, and run `x-ui encrypt-tokens` again.

## Logging & binaries

Variable | Default | Description | 
`XUI_LOG_LEVEL` | `info` | `debug`, `info`, `notice`, `warning`, or `error`. | 
`XUI_DEBUG` | `false` | Debug mode (forces log level to `debug`). | 
`XUI_LOG_FOLDER` | `/var/log/x-ui` | Log output directory. | 
`XUI_BIN_FOLDER` | `bin` | Folder for the Xray-core binary and geosite/geoip files. | 

## Memory & profiling

The panel keeps memory low via `GOGC` and periodic releases. These are advanced
knobs — leave them unset unless you're tuning a constrained host.

Variable | Default | Description | 
`XUI_GOGC` | — | Go GC target percentage; lower = less RAM, slightly more CPU. | 
`XUI_MEMORY_RELEASE_INTERVAL` | — | Minutes between `FreeOSMemory` calls; `0` disables. | 
`XUI_MEMORY_LIMIT` | — | Go soft memory limit in MiB. | 
`GOMEMLIMIT` | — | Go-syntax soft limit (e.g. `400MiB`); takes precedence over above. | 
`XUI_PPROF` | `false` | Expose pprof profiling on `127.0.0.1:6060`. | 

## Xray

Variable | Default | Description | 
`XRAY_VMESS_AEAD_FORCED` | `false` | Force VMess AEAD. | 

## Tunnel health monitor

Optional watchdog: it probes a URL (optionally through a local Xray inbound)
and restarts Xray after repeated failures. A restart drops all connected
clients, so enable it deliberately.

Variable | Default | Description | 
`XUI_TUNNEL_HEALTH_MONITOR` | `false` | Enable the monitor. | 
`XUI_TUNNEL_HEALTH_PROXY` | — | Proxy to send the probe through, e.g. `socks5://127.0.0.1:1080`. Empty = only checks host connectivity. | 
`XUI_TUNNEL_HEALTH_URL` | `https://www.cloudflare.com/cdn-cgi/trace` | URL to probe. | 
`XUI_TUNNEL_HEALTH_INTERVAL` | `30s` | Interval between probes. | 
`XUI_TUNNEL_HEALTH_TIMEOUT` | `10s` | Per-probe timeout. | 
`XUI_TUNNEL_HEALTH_FAILURES` | `3` | Consecutive failures before a restart. | 
`XUI_TUNNEL_HEALTH_COOLDOWN` | `5m` | Minimum delay between restarts. | 

## Unattended install

Variable | Description | 
`XUI_NONINTERACTIVE` | Set to `1` (or run with no TTY) to install with zero prompts; generated credentials are written to `/etc/x-ui/install-result.env`. See Installation. |


=== SOURCE: https://docs.sanaei.dev/docs/reference/ports-firewall
# Ports & Firewall
The ports 3x-ui uses by default and ready-made ufw / nftables rules to open them.

Open only the ports you actually use. Below are the common ones and a generator
for `ufw` and `nftables` rules.

## Common ports

Port (default) | Purpose | 
`22` | SSH (keep this open!). | 
`2053` | Panel (configurable). | 
`2096` | Subscription server (if separate). | 
`443` | A common inbound port (TLS / REALITY). | 
`80` / `443` | Reverse proxy (if you run one). | 

Your actual inbound ports depend on the inbounds you create.

## Generate firewall rules

### 

Allow SSH (port 22)panel — 2053/tcpsubscription — 2096/tcpinbound (HTTPS) — 443/tcpinbound (UDP) — 443/udp

ufw
`ufw allow 22/tcp # SSH
ufw allow 2053/tcp # panel
ufw allow 443/tcp # inbound (HTTPS)
ufw enable`

nftables (/etc/nftables.conf)
`#!/usr/sbin/nft -f

flush ruleset

table inet filter {
 chain input {
 type filter hook input priority 0; policy drop;

 iif "lo" accept
 ct state established,related accept
 icmp type echo-request accept
 tcp dport 22 accept # SSH
 tcp dport 2053 accept # panel
 tcp dport 443 accept # inbound (HTTPS)
 }

 chain forward {
 type filter hook forward priority 0; policy drop;
 }

 chain output {
 type filter hook output priority 0; policy accept;
 }
}`

Always keep SSH allowed before enabling a default-deny policy, and test from a
second session so you don't lock yourself out.

## Related

### Security
Fail2ban, IP limits, and hardening.

### Environment variables
XUI_PORT and friends.
