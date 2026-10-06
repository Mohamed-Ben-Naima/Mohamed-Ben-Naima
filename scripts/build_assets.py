#!/usr/bin/env python3
"""Build the arcade-themed SVGs used by the profile README.

Every image lives in ../assets and is fully self-contained: fonts are
subset to the glyphs each file uses and embedded as WOFF2, animations are
SMIL/CSS only (GitHub strips scripts), so they render the same everywhere.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Fonts (all SIL OFL) are downloaded once into scripts/.fonts/. Brand icons
come from Simple Icons (CC0), vendored in scripts/icons.json.

With GITHUB_TOKEN set (as in the render-readme workflow) the scoreboard is
refreshed from the GitHub API and cached in scripts/stats.json; without it
the cached numbers are reused. The workflow passes the STATS_TOKEN secret
when it exists, so a personal token can count private contributions too.

Edit the CONTENT section below to change text, skills or projects.
"""

import base64
import datetime as dt
import io
import json
import os
import urllib.request
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
FONT_DIR = os.path.join(ROOT, "scripts", ".fonts")
ICONS = json.load(open(os.path.join(ROOT, "scripts", "icons.json"), encoding="utf-8"))
STATS_CACHE = os.path.join(ROOT, "scripts", "stats.json")
FONT_SRC = {
    "pixel": "https://raw.githubusercontent.com/google/fonts/main/ofl/pressstart2p/PressStart2P-Regular.ttf",
    "serif": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "sans": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
}

# ── Palette ───────────────────────────────────────────────────────────────
INK = "#07050f"        # cabinet lacquer
VELVET = "#120c26"     # screen / card body
VELVET_2 = "#1b1338"
GOLD = "#d4af37"
GOLD_HI = "#fbf3d9"
GOLD_MID = "#ecd28c"
GOLD_LO = "#b48a3a"
VIOLET = "#8b5cf6"
VIOLET_HI = "#a78bfa"
LILAC = "#c9bdf0"
ICON = "#ece6ff"
MUTED = "#8a7bb8"
PHOSPHOR = "#5eead4"   # used sparingly: CRT glow accents
RED = "#ff5d73"

# ── CONTENT ───────────────────────────────────────────────────────────────
OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "Mohamed-Ben-Naima")
NAME = "Mohamed Ben Naima"
ROLE = "FULL-STACK DEV · CYBERSECURITY · CLOUD"

TICKER = ("SECURE THE STACK · SHIP THE VISION ★ FULL-STACK · CLOUD · CYBERSECURITY ★ "
          "CTFS · HACKATHONS · COMMUNITIES ★ BASED IN MAHDIA · BUILDING GLOBALLY ★ ")

ATTRIBUTES = [  # label, 0-100, rank
    ("FULL-STACK DEV", 90, "S"),
    ("CYBERSECURITY", 86, "S"),
    ("NETWORKING", 82, "A"),
    ("CLOUD & DEVOPS", 78, "A"),
    ("DATABASES", 76, "A"),
    ("TEAM PLAY", 92, "S"),
]

QUESTS = [  # when, role, where, line, current?
    ("JUL – SEP 2026", "Software Engineering Intern · Full-Stack", "Polymaille (textile industry) · Ksar Hellal",
     "Delivered the Microtiss Confect ERP: purchase, stock, production and sales in one source of truth, secured with RBAC.", True),
    ("MAR 2024 – AUG 2025", "Full-Stack / Backend / Mobile Developer", "Alfa Computers · Mahdia",
     "Built The Hive trading backend, a solo MERN e-commerce shipped via GitLab CI/CD, and led a 3-person IoT team.", False),
    ("2024 – NOW", "Engineering Degree · Cybersecurity & Cloud", "ESPRIM · Monastir",
     "Top of class. Seeking a PFE internship to close the engineering cycle.", False),
    ("2021 – 2024", "BSc Software Engineering", "ISIMa · Mahdia",
     "Graduated with highest honours. Hermes Suite was born here.", False),
]

PROJECTS = [  # title, world, icon, description, tech, badge, status
    ("Microtiss Confect ERP", "WORLD 1-1", "factory",
     "Full-cycle industrial ERP for a textile manufacturer: supplier orders, approvals, stock, "
     "production, invoices and payments, shared across teams with granular RBAC.",
     ["ERP", "REST API", "RBAC", "SQL"], "★ IN PRODUCTION", "NOW PLAYING"),
    ("Hermes Suite", "WORLD 1-2", "cart",
     "MERN e-commerce platform with catalogue, cart, checkout, orders and PDF invoices, now "
     "being matured into a multi-tenant SaaS.",
     ["React", "Node.js", "Express", "MongoDB"], None, "IN PROGRESS"),
    ("Secured Banking Infra", "WORLD 2-1", "bank",
     "Microservices banking app on a private OpenStack cloud in GNS3: dual pfSense, VLANs, "
     "Kafka, KYC with JWT/RBAC and full observability.",
     ["Spring Boot", "Angular", "Kafka", "OpenStack"], "★ NOMINEE", "CLEARED"),
    ("The Hive", "WORLD 2-2", "bolt",
     "Trading platform backend serving the web client through fully authenticated REST "
     "endpoints, with Swagger docs and Postman suites.",
     ["FastAPI", "JWT", "OAuth2", "Swagger"], None, "CLEARED"),
    ("Smart Home IoT", "WORLD 3-1", "house",
     "Led a team of three to ship a mobile app streaming live Arduino sensor data and "
     "controlling LEDs from the phone.",
     ["React Native", "Node.js", "Arduino", "Render"], "★ TEAM LEAD", "CLEARED"),
    ("Windows Server Lab", "WORLD 3-2", "server",
     "Windows Server roles (FTP, DNS, DHCP) with Active Directory, Kerberos-based "
     "authentication and granular file permissions.",
     ["Windows Server", "AD", "Kerberos", "DNS"], None, "CLEARED"),
]

INVENTORY = [  # column, category, [(label, simple-icon slug or monogram)]
    (0, "LANGUAGES", [("Python", "python"), ("JavaScript", "javascript"), ("TypeScript", "typescript"),
                      ("Java", "openjdk"), ("PHP", "php"), ("SQL", "=SQL")]),
    (0, "FRONTEND", [("Angular", "angular"), ("React", "react"), ("React Native", "react"),
                     ("Tailwind", "tailwindcss"), ("HTML/CSS", "html5")]),
    (0, "BACKEND & APIS", [("FastAPI", "fastapi"), ("Node.js", "nodedotjs"), ("Express", "express"),
                           ("Spring Boot", "springboot"), ("Symfony", "symfony"), ("Swagger", "swagger")]),
    (0, "DATABASES", [("MongoDB", "mongodb"), ("PostgreSQL", "postgresql"), ("MySQL", "mysql"),
                      ("Oracle", "=ORA")]),
    (0, "TOOLS", [("Git", "git"), ("Postman", "postman"), ("Jira", "jira"), ("n8n", "n8n")]),
    (1, "SECURITY & AUTH", [("JWT", "jsonwebtokens"), ("OAuth2", "=OA2"), ("RBAC", "=RBAC"),
                            ("Keycloak", "keycloak"), ("Wazuh", "=WZH"), ("Kali", "kalilinux")]),
    (1, "CLOUD & DEVOPS", [("Docker", "docker"), ("Kubernetes", "kubernetes"), ("OpenStack", "openstack"),
                           ("AWS", "=AWS"), ("GitLab CI", "gitlab"), ("Actions", "githubactions")]),
    (1, "NETWORK & OS", [("Cisco", "cisco"), ("pfSense", "pfsense"), ("Wireshark", "wireshark"),
                         ("VLANs", "=VLAN"), ("Ubuntu", "ubuntu"), ("Win Server", "=WIN")]),
    (1, "OBSERVABILITY", [("Grafana", "grafana"), ("Prometheus", "prometheus"), ("Loki", "=LOKI"),
                          ("Kafka", "apachekafka")]),
]

ACHIEVEMENTS = [  # icon, title, subtitle, points
    ("trophy", "Projects Ball · Nominee", "Secured Banking Infrastructure", "100G"),
    ("medal", "CTF Podium · 2nd & 4th", "Polytech Sousse CTF with Hunters Club", "90G"),
    ("star", "Hackathon · 2nd Place", "Clean & Green hackathon 2025", "80G"),
    ("crown", "Guild Founder", "Co-founded Hunters Club, 20+ CTF players", "75G"),
    ("cap", "Highest Honours", "BSc at ISIMa · top of class at ESPRIM", "120G"),
    ("shield", "Red Team Certified", "CLLMSP & CRTOM · CCNA in progress", "60G"),
]

SIDE_QUESTS = [  # icon, title, line
    ("dumbbell", "GYM", "Discipline, in the terminal and out of it."),
    ("knight", "CHESS", "Thinking moves ahead, like hunting edge cases."),
    ("book", "BOOKS", "Security, systems and the odd page of fiction."),
    ("glove", "KICKBOXING", "Problem-solving with solid form."),
]

BUTTONS = [  # file, label, icon (slug, =monogram or sprite:name), primary?
    ("btn-portfolio", "PORTFOLIO", "netlify", False),
    ("btn-linkedin", "LINKEDIN", "=in", False),
    ("btn-cv", "DOWNLOAD CV", "sprite:doc", True),
    ("btn-email", "EMAIL", "gmail", False),
    ("btn-github", "GITHUB", "github", False),
    ("btn-tryhackme", "TRYHACKME", "tryhackme", False),
]

STAGES = {  # file: (stage label, title)
    "h-player": ("STAGE 01 · PLAYER SELECT", "The Player"),
    "h-quests": ("STAGE 02 · QUEST LOG", "Experience"),
    "h-projects": ("STAGE 03 · LEVEL SELECT", "Featured Work"),
    "h-stack": ("STAGE 04 · INVENTORY", "Tech Arsenal"),
    "h-trophies": ("STAGE 05 · HALL OF FAME", "Achievements"),
    "h-stats": ("STAGE 06 · SCOREBOARD", "GitHub Stats"),
    "h-snake": ("STAGE 07 · BONUS ROUND", "Contribution Arcade"),
    "h-beyond": ("STAGE 08 · SIDE QUESTS", "Beyond the Code"),
}

# ── Pixel sprites (X = filled; letters map to palette in sprite()) ───────
SPRITES = {
    "invader_a": ["..X.....X..", "...X...X...", "..XXXXXXX..", ".XX.XXX.XX.",
                  "XXXXXXXXXXX", "X.XXXXXXX.X", "X.X.....X.X", "...XX.XX..."],
    "invader_b": ["..X.....X..", "X..X...X..X", "X.XXXXXXX.X", "XXX.XXX.XXX",
                  "XXXXXXXXXXX", ".XXXXXXXXX.", "..X.....X..", ".X.......X."],
    "ghost": ["...XXXX...", ".XXXXXXXX.", "XXXXXXXXXX", "XX..XX..XX", "XX..XX..XX",
              "XXXXXXXXXX", "XXXXXXXXXX", "XXXXXXXXXX", "XX.XX.XX.X", "X...X...X."],
    "factory": [".........", "X........", "X.X......", "X.X.X....", "XXXXXXXXX",
                "XXXXXXXXX", "X.X.X.X.X", "XXXXXXXXX", "XXXXXXXXX"],
    "cart": ["XX.......", ".X.......", ".XXXXXXXX", ".X.....X.", ".X....X..",
             ".XXXXXX..", ".X.......", "..X...X..", "........."],
    "bank": ["....X....", "..XXXXX..", "XXXXXXXXX", ".........", ".X.X.X.X.",
             ".X.X.X.X.", ".X.X.X.X.", ".........", "XXXXXXXXX"],
    "bolt": [".....XXX.", "....XXX..", "...XXX...", "..XXXXXX.", "....XXX..",
             "...XXX...", "..XX.....", ".XX......", "X........"],
    "house": ["....X....", "...XXX...", "..XXXXX..", ".XXXXXXX.", "XXXXXXXXX",
              ".X.....X.", ".X.XX..X.", ".X.XX..X.", ".XXXXXXX."],
    "server": ["XXXXXXXXX", "X.......X", "X.XX..X.X", "XXXXXXXXX", "X.......X",
               "X.XX..X.X", "XXXXXXXXX", "...X.X...", ".XXXXXXX."],
    "doc": ["XXXXXX...", "X....XX..", "X.XX.XXX.", "X......X.", "X.XXXX.X.",
            "X......X.", "X.XXXX.X.", "X......X.", "XXXXXXXX."],
    "trophy": ["XXXXXXXXX", "XXXXXXXXX", "X.XXXXX.X", "X.XXXXX.X", ".XXXXXXX.",
               "..XXXXX..", "...XXX...", "....X....", "..XXXXX.."],
    "medal": ["XX.....XX", ".XX...XX.", "..XX.XX..", "...XXX...", "..XXXXX..",
              ".XXX.XXX.", ".XX...XX.", ".XXX.XXX.", "..XXXXX.."],
    "star": ["....X....", "....X....", "...XXX...", "XXXXXXXXX", ".XXXXXXX.",
             "..XXXXX..", "..XX.XX..", ".XX...XX.", ".X.....X."],
    "crown": [".........", "X...X...X", "XX.XXX.XX", "XXXXXXXXX", "XXXXXXXXX",
              "XX.XXX.XX", "XXXXXXXXX", "XXXXXXXXX", "........."],
    "cap": ["....X....", "..XXXXX..", "XXXXXXXXX", ".XXXXXXX.", "..XXXXX.X",
            "..X...X.X", "..XXXXX.X", "......XXX", "........."],
    "shield": ["XXXXXXXXX", "X...X...X", "X...X...X", "XXXXXXXXX", "X...X...X",
               ".X..X..X.", ".X..X..X.", "..X.X.X..", "....X...."],
    "flame": ["....X....", "...XX....", "...XXX...", "..XXXX.X.", "..XXXXXX.",
              ".XXX.XXXX", ".XX...XXX", ".XX...XX.", "..XXXXX.."],
    "dumbbell": [".........", ".X.....X.", "XX.....XX", "XX.....XX", "XXXXXXXXX",
                 "XX.....XX", "XX.....XX", ".X.....X.", "........."],
    "knight": ["...XX....", "..XXXX...", ".XX.XXX..", "XXXXXXXX.", "....XXX..",
               "...XXXX..", "..XXXXX..", ".XXXXXXX.", ".XXXXXXX."],
    "book": ["XXXX.XXXX", "X..XXX..X", "X..XXX..X", "X..XXX..X", "X..XXX..X",
             "X..XXX..X", "XXXXXXXXX", "....X....", "........."],
    "glove": ["..XXXXX..", ".XXXXXXX.", ".XXXXXXXX", ".XXXXXXXX", ".XXXXXXX.",
              ".XXXXXXX.", "..XXXXX..", "..XXXXX..", "..XXXXX.."],
    "coin": ["..XXXX..", ".XXXXXX.", "XXX..XXX", "XX.XX.XX", "XX.XX.XX", "XXX..XXX",
             ".XXXXXX.", "..XXXX.."],
    # Player sprite: h hood, H hood light, k shadow, e eyes, g gold, l laptop, L screen
    "hero": [".....hhhhhh.....", "...hhHHHHHHhh...", "..hHHHHHHHHHHh..",
             ".hHHHkkkkkkHHHh.", ".hHHkkkkkkkkHHh.", ".hHHkkekkekkHHh.",
             ".hHHkkkkkkkkHHh.", ".hHHHkkkkkkHHHh.", "..hHHHHggHHHHh..",
             ".hhHHHHggHHHHhh.", "hHHHHHHHHHHHHHHh", "hHHlllllllllHHHh",
             "hHHllllgllllHHHh", "hHHlllllllllHHHh", "hhLLLLLLLLLLLLhh",
             ".hhhhhhhhhhhhhh."],
}
HERO_PALETTE = {"h": "#3b2470", "H": "#5b3aa8", "k": "#0a0716", "e": "#ffd166",
                "g": GOLD, "l": "#2a2440", "L": "#3a325a"}


# ── Fonts: download, measure, subset, embed ───────────────────────────────
_FONTS = {}


def font_path(key):
    os.makedirs(FONT_DIR, exist_ok=True)
    path = os.path.join(FONT_DIR, key + ".ttf")
    if not os.path.exists(path):
        urllib.request.urlretrieve(FONT_SRC[key], path)
    return path


def load_font(key, weight):
    if (key, weight) not in _FONTS:
        font = TTFont(font_path(key))
        if "fvar" in font:
            font = instancer.instantiateVariableFont(font, {"wght": weight})
        _FONTS[key, weight] = font
    return _FONTS[key, weight]


def font_weight(font, weight):
    return {"pixel": 400, "serif": 700}.get(font, weight)


def measure(s, font="sans", size=12, weight=500):
    """Advance width of s in px, from the real font metrics."""
    f = load_font(font, font_weight(font, weight))
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(c), cmap[32])][0] for c in s) * size / upm


def wrap(s, width, font="sans", size=12, weight=500):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if cur and measure(trial, font, size, weight) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def woff2(key, weight, chars):
    font = TTFont(font_path(key))
    if "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": weight})
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(chars))) + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


FAMILY = {"pixel": ("PX", "'Courier New',monospace"),
          "serif": ("PF", "Georgia,serif"),
          "sans": ("SG", "'Segoe UI',system-ui,sans-serif")}


class Svg:
    """Collects markup and the glyphs used per embedded font face."""

    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.parts, self.defs, self.css = [], [], []
        self.glyphs = {}

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, font="pixel", size=12, fill=GOLD, anchor="start",
             extra="", weight=500):
        w = font_weight(font, weight)
        self.glyphs.setdefault((font, w), set()).update(s)
        fam, fallback = FAMILY[font]
        return (f'<text x="{x:g}" y="{y:g}" font-family="{fam},{fallback}" font-size="{size}" '
                f'font-weight="{w}" fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')

    def render(self):
        faces = "".join(
            f"@font-face{{font-family:{FAMILY[key][0]};font-weight:{w};"
            f"src:url(data:font/woff2;base64,{woff2(key, w, chars)}) format('woff2');}}"
            for (key, w), chars in sorted(self.glyphs.items()))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}">\n'
                f'<style>{faces}{"".join(self.css)}</style>\n<defs>{"".join(self.defs)}</defs>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


def sprite(name, x, y, px, fill=GOLD, palette=None, extra=""):
    """Pixel bitmap as one path per colour."""
    paths = {}
    for r, row in enumerate(SPRITES[name]):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            colour = palette[ch] if palette else fill
            paths.setdefault(colour, []).append(
                f"M{x + c * px:g} {y + r * px:g}h{px:g}v{px:g}h-{px:g}z")
    return "".join(f'<path d="{"".join(d)}" fill="{col}" {extra}/>' for col, d in paths.items())


def icon(svg, ref, cx, cy, size, fill=ICON):
    """Simple Icons glyph, '=TXT' monogram or 'sprite:name', centred on (cx, cy)."""
    if ref.startswith("sprite:"):
        rows = SPRITES[ref[7:]]
        px = size / len(rows)
        return sprite(ref[7:], cx - len(rows[0]) * px / 2, cy - size / 2, px, fill)
    if ref.startswith("="):
        txt = ref[1:]
        fs = min(size * .52, size * 1.5 / len(txt))
        return svg.text(cx, cy + fs / 2, txt, "pixel", round(fs, 1), fill, "middle")
    k = size / 24
    return (f'<path d="{ICONS[ref]}" fill="{fill}" '
            f'transform="translate({cx - size / 2:g} {cy - size / 2:g}) scale({k:g})"/>')


def common_defs(svg):
    svg.defs.append(f"""
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{GOLD_HI}"/><stop offset=".55" stop-color="{GOLD_MID}"/><stop offset="1" stop-color="#c99842"/></linearGradient>
<linearGradient id="goldV" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{GOLD_HI}"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_LO}"/></linearGradient>
<linearGradient id="trim" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{GOLD_MID}"/><stop offset=".5" stop-color="{GOLD_LO}"/><stop offset="1" stop-color="{GOLD_MID}"/></linearGradient>
<radialGradient id="screen" cx=".5" cy=".45" r=".75">
  <stop offset="0" stop-color="{VELVET_2}"/><stop offset=".7" stop-color="{VELVET}"/><stop offset="1" stop-color="#05030b"/></radialGradient>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
  <rect width="4" height="1.6" fill="#000" opacity=".32"/></pattern>
<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<filter id="glow" x="-20%" y="-50%" width="140%" height="200%">
  <feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="softglow" x="-20%" y="-50%" width="140%" height="200%">
  <feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
""")
    svg.css.append("""
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.flicker{animation:flicker 5s infinite}
@keyframes flicker{0%,100%{opacity:1}47%{opacity:1}48%{opacity:.86}49%{opacity:1}82%{opacity:.93}83%{opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""")


def crt(svg, x, y, w, h, r=22):
    """Screen body; returns the overlay (scanlines + glare) to add last."""
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#screen)"/>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#scan)"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="#000" stroke-opacity=".6" stroke-width="6"/>'
            f'<path d="M{x + 18} {y + 40} Q{x + 18} {y + 16} {x + 60} {y + 14} L{x + w * .42:g} {y + 12}" '
            f'stroke="#fff" stroke-opacity=".07" stroke-width="6" fill="none" stroke-linecap="round"/>')


def frame(svg, w, h, inset=2):
    svg.add(f'<rect x="{inset}" y="{inset}" width="{w - 2 * inset}" height="{h - 2 * inset}" rx="20" '
            f'fill="{INK}" stroke="url(#trim)" stroke-width="2"/>')


def write(name, svg):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg.render())
    print(f"  {name}.svg  {os.path.getsize(path) / 1024:.1f} KB")


# ── Hero: arcade cabinet title screen ─────────────────────────────────────
def hero():
    W, H = 1000, 460
    s = Svg(W, H, f"{NAME}: Full-Stack Developer and Cybersecurity & Cloud Engineer")
    common_defs(s)
    s.css.append("""
.bulb{animation:chase .9s steps(1) infinite}
@keyframes chase{0%{opacity:1}33%{opacity:.18}}
.march{animation:march 6s ease-in-out infinite alternate}
@keyframes march{to{transform:translateX(120px)}}
.fa{animation:fa 1s steps(1) infinite}.fb{animation:fa 1s steps(1) infinite -.5s}
@keyframes fa{50%{opacity:0}}
.bob{animation:bob 2.4s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-6px)}}
""")
    frame(s, W, H)

    # Marquee with chasing bulbs
    s.add(f'<rect x="22" y="20" width="{W - 44}" height="78" rx="14" fill="#140d2c" stroke="{GOLD_LO}" stroke-width="1.2"/>')
    s.add(f'<rect x="22" y="20" width="{W - 44}" height="78" rx="14" fill="url(#scan)" opacity=".5"/>')
    bulbs = []
    for i, bx in enumerate(range(44, W - 30, 26)):
        for by in (31, 87):
            bulbs.append(f'<circle cx="{bx}" cy="{by}" r="3.2" fill="{GOLD_MID}" class="bulb" '
                         f'style="animation-delay:-{(i % 3) * .3:.1f}s"/>')
    s.add(f'<g filter="url(#softglow)">{"".join(bulbs)}</g>')
    s.add(s.text(W / 2, 69, "★ BEN NAIMA ARCADE ★", size=22, fill="url(#goldV)", anchor="middle",
                 extra='filter="url(#softglow)" letter-spacing="2"'))

    # Screen
    sx, sy, sw, sh = 40, 112, W - 80, 268
    overlay = crt(s, sx, sy, sw, sh)
    g = [s.text(72, 148, "1UP", fill=RED, extra='class="blink"'),
         s.text(72, 166, "MOHAMED", fill=LILAC),
         s.text(W / 2, 148, "HI-SCORE", fill=RED, anchor="middle"),
         s.text(W / 2, 166, "999999", fill=LILAC, anchor="middle"),
         s.text(W - 72, 148, "CREDIT", fill=RED, anchor="end"),
         s.text(W - 72, 166, "01", fill=LILAC, anchor="end")]

    inv = []
    for i, x in enumerate(range(250, 640, 64)):
        col = GOLD if i % 2 == 0 else VIOLET_HI
        inv.append(f'<g class="fa">{sprite("invader_a", x, 184, 3, col)}</g>'
                   f'<g class="fb">{sprite("invader_b", x, 184, 3, col)}</g>')
    g.append(f'<g class="march" opacity=".9">{"".join(inv)}</g>')

    g.append(f'<ellipse cx="{W / 2}" cy="262" rx="330" ry="46" fill="{VIOLET}" opacity=".10" filter="url(#glow)"/>')
    s.defs.append(f'<clipPath id="nameClip">{s.text(W / 2, 278, NAME, "serif", 62, anchor="middle")}</clipPath>')
    g.append(s.text(W / 2, 278, NAME, "serif", 62, "url(#gold)", "middle", 'filter="url(#softglow)"'))
    g.append(f'<rect x="-200" y="220" width="160" height="70" fill="url(#shine)" clip-path="url(#nameClip)">'
             f'<animateTransform attributeName="transform" type="translate" values="0,0;1400,0;1400,0" '
             f'keyTimes="0;.6;1" dur="5s" repeatCount="indefinite"/></rect>')
    g.append(s.text(W / 2, 314, ROLE, size=13, fill=LILAC, anchor="middle", extra='letter-spacing="1"'))
    g.append(f'<g class="blink">{s.text(W / 2 + 10, 352, "PRESS START", size=15, fill=GOLD, anchor="middle")}'
             f'<path d="M{W / 2 - 96} 340 l12 6 l-12 6z" fill="{GOLD}"/></g>')
    g.append(s.text(72, 362, "© 2026 MAHDIA · TN", size=10, fill=MUTED))
    g.append(s.text(W - 72, 362, "ESPRIM ENG.", size=10, fill=MUTED, anchor="end"))
    g.append(f'<g class="bob">{sprite("hero", 820, 186, 4, palette=HERO_PALETTE)}</g>')
    g.append(f'<g class="bob" style="animation-delay:-1.2s">{sprite("ghost", 120, 196, 4, RED)}'
             f'<rect x="128" y="208" width="4" height="4" fill="#fff"/><rect x="144" y="208" width="4" height="4" fill="#fff"/></g>')
    s.add(f'<g class="flicker">{"".join(g)}</g>')
    s.add(overlay)

    # Control deck
    s.add(f'<rect x="22" y="392" width="{W - 44}" height="48" rx="12" fill="#100a22" stroke="{GOLD_LO}" stroke-opacity=".6"/>')
    swing = 'values="0 112 417;-18 112 417;0 112 417;18 112 417;0 112 417" dur="4s" repeatCount="indefinite"'
    s.add(f'<rect x="90" y="413" width="44" height="8" rx="4" fill="#05030b"/>'
          f'<line x1="112" y1="417" x2="112" y2="400" stroke="#cfc6e6" stroke-width="4" stroke-linecap="round">'
          f'<animateTransform attributeName="transform" type="rotate" {swing}/></line>'
          f'<circle cx="112" cy="400" r="8" fill="{VIOLET}"><animateTransform attributeName="transform" type="rotate" {swing}/></circle>')
    for i, (bx, col) in enumerate(((W - 200, GOLD), (W - 160, VIOLET_HI), (W - 120, RED))):
        s.add(f'<circle cx="{bx}" cy="416" r="11" fill="#05030b"/>'
              f'<circle cx="{bx}" cy="414" r="10" fill="{col}"><animate attributeName="cy" values="414;416;414;414" '
              f'keyTimes="0;.05;.1;1" dur="3s" begin="{i * .4:.1f}s" repeatCount="indefinite"/></circle>')
    s.add(s.text(W / 2, 422, "SECURE THE STACK · SHIP THE VISION", size=11, fill=MUTED, anchor="middle"))
    write("hero", s)


# ── LED ticker ────────────────────────────────────────────────────────────
def ticker():
    W, H, size = 1000, 50, 14
    s = Svg(W, H, "Rotating taglines")
    common_defs(s)
    span = len(TICKER) * size
    s.defs.append(f'<linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GOLD_MID}"/>'
                  f'<stop offset="1" stop-color="{VIOLET_HI}"/></linearGradient>'
                  f'<pattern id="grid" width="3" height="3" patternUnits="userSpaceOnUse"><path d="M0 0h3v3h-3z M0 0h2v2h-2z" '
                  f'fill="{INK}" fill-rule="evenodd" opacity=".7"/></pattern>'
                  f'<clipPath id="tc"><rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="10"/></clipPath>')
    s.add(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="12" fill="#0b0716" stroke="url(#trim)" stroke-width="1.5"/>')
    run = (s.text(0, 32, TICKER, size=size, fill="url(#tg)") +
           s.text(span, 32, TICKER, size=size, fill="url(#tg)"))
    s.add(f'<g clip-path="url(#tc)" filter="url(#softglow)"><g>{run}'
          f'<animateTransform attributeName="transform" type="translate" from="0,0" to="-{span},0" '
          f'dur="{span / 60:.0f}s" repeatCount="indefinite"/></g></g>')
    s.add(f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="10" fill="url(#grid)"/>')
    write("ticker", s)


# ── Divider & stage headers ───────────────────────────────────────────────
def divider():
    W, H = 1000, 30
    s = Svg(W, H, "divider")
    common_defs(s)
    s.add("".join(
        f'<rect x="{x}" y="13" width="4" height="4" fill="{GOLD}" opacity=".55">'
        f'<animate attributeName="opacity" values=".55;.55;0;0;.55" keyTimes="0;{(x - 40) / 950 * .8:.3f};{(x - 40) / 950 * .8 + .01:.3f};.95;1" '
        f'dur="8s" repeatCount="indefinite"/></rect>'
        for x in range(40, 961, 28)))
    open_, shut = "M10 15 L20 6 A12 12 0 1 0 20 24 Z", "M10 15 L22 13 A12 12 0 1 0 22 17 Z"
    s.add(f'<g><path fill="#ffd166" d="{open_}"><animate attributeName="d" dur=".35s" repeatCount="indefinite" '
          f'values="{open_};{shut};{open_}"/></path>'
          f'<animateTransform attributeName="transform" type="translate" values="20,0;990,0;990,0" keyTimes="0;.8;1" '
          f'dur="8s" repeatCount="indefinite"/></g>')
    write("divider", s)


def stage_header(name, label, title):
    W, H = 1000, 96
    s = Svg(W, H, title)
    common_defs(s)
    s.defs.append(f'<linearGradient id="fadeL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{GOLD}" stop-opacity=".7"/></linearGradient>'
                  f'<linearGradient id="fadeR" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GOLD}" stop-opacity=".7"/>'
                  f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>')
    pw, c = 420, 12
    x0 = (W - pw) / 2
    s.add(f'<line x1="40" y1="52" x2="{x0 - 14}" y2="52" stroke="url(#fadeL)"/>'
          f'<line x1="{x0 + pw + 14}" y1="52" x2="{W - 40}" y2="52" stroke="url(#fadeR)"/>')
    plaque = f'M{x0 + c} 8h{pw - 2 * c}l{c} {c}v{H - 16 - 2 * c}l-{c} {c}h-{pw - 2 * c}l-{c} -{c}v-{H - 16 - 2 * c}z'
    s.add(f'<path d="{plaque}" fill="{VELVET}" stroke="url(#trim)" stroke-width="1.6"/><path d="{plaque}" fill="url(#scan)"/>')
    s.add(s.text(W / 2, 34, label, size=10, fill=VIOLET_HI, anchor="middle", extra='letter-spacing="1"'))
    s.add(s.text(W / 2, 70, title, "serif", 30, "url(#gold)", "middle", 'filter="url(#softglow)"'))
    s.add(f'<g class="blink"><path d="M{x0 + 26} 54 l10 6 l-10 6z" fill="{GOLD}"/>'
          f'<path d="M{x0 + pw - 26} 54 l-10 6 l10 6z" fill="{GOLD}"/></g>')
    write(name, s)


# ── Player card ───────────────────────────────────────────────────────────
def player():
    W, H = 1000, 400
    s = Svg(W, H, "Player card: " + ", ".join(f"{a} rank {r}" for a, _, r in ATTRIBUTES))
    common_defs(s)
    s.css.append(".bob{animation:bob 2.4s ease-in-out infinite}@keyframes bob{50%{transform:translateY(-5px)}}"
                 ".pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.55}}")
    frame(s, W, H)

    overlay = crt(s, 26, 26, 300, 348, 16)
    s.add(f'<ellipse cx="176" cy="204" rx="90" ry="14" fill="{VIOLET}" opacity=".25" filter="url(#glow)"/>')
    s.add(f'<g class="bob">{sprite("hero", 112, 64, 8, palette=HERO_PALETTE)}'
          f'<g class="blink" style="animation-duration:3.2s">'
          f'<rect x="152" y="104" width="8" height="8" fill="#0a0716"/><rect x="176" y="104" width="8" height="8" fill="#0a0716"/></g>'
          f'<rect x="136" y="176" width="80" height="8" fill="{PHOSPHOR}" opacity=".35" class="pulse"/></g>')
    s.add(s.text(176, 250, "MOHAMED", size=18, fill="url(#goldV)", anchor="middle", extra='filter="url(#softglow)"'))
    s.add(s.text(176, 276, "CLASS: SEC-DEV", size=11, fill=LILAC, anchor="middle"))
    s.add(s.text(176, 296, "BASE: MAHDIA, TN", size=11, fill=MUTED, anchor="middle"))
    s.add(s.text(176, 316, "LANG: AR FR EN DE", size=11, fill=MUTED, anchor="middle"))
    s.add(f'<g class="blink">{s.text(176, 350, "P1 READY", size=12, fill=PHOSPHOR, anchor="middle")}</g>')
    s.add(overlay)

    s.add(s.text(360, 56, "ATTRIBUTES", size=14, fill=GOLD))
    s.add(f'<line x1="360" y1="68" x2="{W - 30}" y2="68" stroke="{GOLD}" stroke-opacity=".25"/>')
    segs, bx, bw = 20, 560, 340
    sw = bw / segs
    for i, (label, val, rank) in enumerate(ATTRIBUTES):
        y = 98 + i * 36
        fill = bw * val / 100
        s.add(s.text(360, y + 11, label, size=11, fill=LILAC))
        s.add(f'<rect x="{bx}" y="{y}" width="{bw}" height="14" fill="#0b0716" stroke="{GOLD_LO}" stroke-opacity=".5"/>')
        s.add(f'<rect x="{bx}" y="{y}" width="{fill:.1f}" height="14" fill="url(#gold)">'
              f'<animate attributeName="width" from="0" to="{fill:.1f}" dur="1.2s" begin="{.3 + i * .18:.2f}s" fill="freeze" '
              f'calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/></rect>')
        s.add("".join(f'<rect x="{bx + k * sw - 1:.1f}" y="{y}" width="2" height="14" fill="#0b0716"/>' for k in range(1, segs)))
        s.add(s.text(bx + bw + 22, y + 13, rank, size=14, fill=GOLD if rank == "S" else VIOLET_HI,
                     extra='filter="url(#softglow)"'))

    qy = 330
    s.add(s.text(360, qy - 14, "CURRENT QUEST", size=10, fill=VIOLET_HI))
    s.add(s.text(360, qy + 6, "Land a PFE internship", "serif", 20, "url(#gold)"))
    s.add(f'<rect x="{bx + 60}" y="{qy - 6}" width="{bw - 60}" height="10" rx="5" fill="#0b0716" stroke="{VIOLET}" stroke-opacity=".6"/>'
          f'<rect x="{bx + 60}" y="{qy - 6}" width="{(bw - 60) * .85:.0f}" height="10" rx="5" fill="{VIOLET}" class="pulse"/>')
    s.add(s.text(bx + bw + 22, qy + 4, "XP", size=10, fill=VIOLET_HI))
    s.add(s.text(360, qy + 36, "SPECIAL MOVES: ERPs THAT SHIP · BREAK & HARDEN · CTFs", size=9, fill=MUTED))
    write("player", s)


# ── Quest log (experience & education timeline) ───────────────────────────
def quest_log():
    W, row = 1000, 118
    H = 40 + row * len(QUESTS) + 10
    s = Svg(W, H, "Quest log: " + "; ".join(f"{q[0]} {q[1]}, {q[2]}" for q in QUESTS))
    common_defs(s)
    frame(s, W, H)
    tx = 250  # timeline spine
    s.add(f'<line x1="{tx}" y1="44" x2="{tx}" y2="{H - 40}" stroke="{GOLD}" stroke-opacity=".35" stroke-width="2" stroke-dasharray="2 6"/>')
    for i, (when, role, where, line, now) in enumerate(QUESTS):
        y = 36 + i * row
        g = [s.text(tx - 34, y + 30, when, size=10, fill=GOLD if now else MUTED, anchor="end")]
        if now:
            g.append(f'<g class="blink">{s.text(tx - 34, y + 52, "▶ NOW", size=10, fill=PHOSPHOR, anchor="end")}</g>')
        g.append(f'<circle cx="{tx}" cy="{y + 26}" r="14" fill="{INK}" stroke="{GOLD if now else GOLD_LO}" stroke-width="1.5"/>')
        g.append(sprite("coin", tx - 8, y + 18, 2, "url(#goldV)" if now else MUTED))
        if now:
            g.append(f'<circle cx="{tx}" cy="{y + 26}" r="14" fill="none" stroke="{GOLD}"><animate attributeName="r" '
                     f'values="14;24" dur="1.6s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0" '
                     f'dur="1.6s" repeatCount="indefinite"/></circle>')
        cx = tx + 36
        g.append(f'<rect x="{cx}" y="{y}" width="{W - cx - 26}" height="{row - 14}" rx="12" fill="{VELVET}" '
                 f'stroke="{GOLD if now else GOLD_LO}" stroke-opacity="{.8 if now else .35}"/>')
        g.append(s.text(cx + 20, y + 30, role, "sans", 18, GOLD_HI, weight=700))
        g.append(s.text(cx + 20, y + 50, where, "sans", 13, VIOLET_HI, weight=500))
        for k, ln in enumerate(wrap(line, W - cx - 66, "sans", 13, 400)[:2]):
            g.append(s.text(cx + 20, y + 72 + k * 18, ln, "sans", 13, LILAC, weight=400))
        s.add("".join(g))
    write("quest-log", s)


# ── Level select (projects) ───────────────────────────────────────────────
def level_select():
    W = 1000
    cw, ch, gx, gy = 462, 262, 488, 282
    rows = (len(PROJECTS) + 1) // 2
    H = 26 * 2 + gy * rows - (gy - ch)
    s = Svg(W, H, "Featured projects: " + "; ".join(p[0] for p in PROJECTS))
    common_defs(s)
    stops = [(f"{k * 100 / len(PROJECTS):.2f}%", (k % 2) * gx, (k // 2) * gy) for k in range(len(PROJECTS))]
    s.css.append(".sel{animation:sel %ds steps(1) infinite}@keyframes sel{%s}"
                 % (len(PROJECTS) * 2.5, "".join(f"{p}{{transform:translate({x}px,{y}px)}}" for p, x, y in stops)))
    frame(s, W, H)
    for i, (title, world, ico, desc, tech, badge, status) in enumerate(PROJECTS):
        x, y = 26 + (i % 2) * gx, 26 + (i // 2) * gy
        now = status == "NOW PLAYING"
        s.add(f'<path d="M{x + 18} {y}h{cw - 36}l18 18v{ch - 18}h-{cw}v-{ch - 18}z" fill="{VELVET}" '
              f'stroke="{GOLD if now else GOLD_LO}" stroke-opacity="{.9 if now else .55}"/>')
        s.add("".join(f'<rect x="{x + cw / 2 - 60 + k * 16}" y="{y + 8}" width="8" height="3" rx="1.5" fill="{GOLD}" opacity=".35"/>'
                      for k in range(8)))
        s.add(f'<rect x="{x + 16}" y="{y + 22}" width="{cw - 32}" height="{ch - 38}" rx="8" fill="url(#screen)"/>')
        s.add(f'<rect x="{x + 16}" y="{y + 22}" width="{cw - 32}" height="{ch - 38}" rx="8" fill="url(#scan)" opacity=".7"/>')
        s.add(f'<rect x="{x + 30}" y="{y + 38}" width="44" height="44" rx="8" fill="#0b0716" stroke="{GOLD}" stroke-opacity=".5"/>')
        s.add(sprite(ico, x + 34, y + 42, 4, GOLD, extra='filter="url(#softglow)"'))
        s.add(s.text(x + 88, y + 52, world, size=9, fill=VIOLET_HI))
        s.add(s.text(x + 88, y + 78, title, "serif", 23, "url(#gold)"))
        if badge:
            bw = len(badge) * 9 + 18
            s.add(f'<rect x="{x + cw - 30 - bw}" y="{y + 38}" width="{bw}" height="20" rx="3" fill="{GOLD}"/>')
            s.add(s.text(x + cw - 30 - bw / 2, y + 52, badge, size=9, fill=INK, anchor="middle"))
        for k, line in enumerate(wrap(desc, cw - 64, "sans", 14, 400)[:3]):
            s.add(s.text(x + 30, y + 110 + k * 21, line, "sans", 14, LILAC, weight=400))
        cx = x + 30
        for t in tech:
            tw = measure(t, "sans", 12, 700) + 20
            s.add(f'<rect x="{cx:.1f}" y="{y + 184}" width="{tw:.1f}" height="22" rx="11" fill="none" stroke="{VIOLET}" stroke-opacity=".8"/>')
            s.add(s.text(cx + tw / 2, y + 199.5, t, "sans", 12, VIOLET_HI, "middle", weight=700))
            cx += tw + 8
        s.add(s.text(x + 30, y + 236, "STATUS:", size=9, fill=MUTED))
        col = PHOSPHOR if status == "CLEARED" else GOLD
        s.add(f'<g class="{"" if status == "CLEARED" else "blink"}">{s.text(x + 100, y + 236, status, size=9, fill=col)}</g>')
    m = 18
    a, b = m + cw + 16, m + ch + 16
    s.add(f'<g class="sel"><path d="M{m} {m}h40M{m} {m}v40M{a} {m}h-40M{a} {m}v40M{m} {b}h40M{m} {b}v-40M{a} {b}h-40M{a} {b}v-40" '
          f'stroke="{GOLD_HI}" stroke-width="3" fill="none" filter="url(#softglow)" class="blink" style="animation-duration:.8s"/></g>')
    write("level-select", s)


# ── Inventory (tech stack) ────────────────────────────────────────────────
def inventory():
    W, pad, colw = 1000, 30, 455
    slot, pitch, label_h = 54, 74, 20
    s = Svg(W, 10, "Tech arsenal: " + "; ".join(f"{c}: " + ", ".join(i[0] for i in items) for _, c, items in INVENTORY))
    common_defs(s)
    s.css.append(".cur{animation:cur 9s steps(1) infinite}")
    per_row = colw // pitch
    ys = [70, 70]
    blocks = []
    for col, cat, items in INVENTORY:
        x0, y0 = pad + col * (colw + 30), ys[col]
        nrows = -(-len(items) // per_row)
        blocks.append((x0, y0, cat, items))
        ys[col] = y0 + 26 + nrows * (slot + label_h + 14) + 14
    H = max(ys) + 6
    s.h = H
    frame(s, W, H)
    s.add(s.text(pad, 44, "INVENTORY", size=14, fill=GOLD))
    total = sum(len(i) for _, _, i in INVENTORY)
    s.add(s.text(W - pad, 44, f"{total} ITEMS EQUIPPED", size=10, fill=VIOLET_HI, anchor="end"))
    s.add(f'<line x1="{pad}" y1="56" x2="{W - pad}" y2="56" stroke="{GOLD}" stroke-opacity=".25"/>')
    slots = []
    for bi, (x0, y0, cat, items) in enumerate(blocks):
        s.add(s.text(x0, y0 + 12, cat, size=10, fill=GOLD_MID))
        s.add(s.text(x0 + colw - 10, y0 + 12, f"x{len(items)}", size=9, fill=MUTED, anchor="end"))
        for k, (label, ref) in enumerate(items):
            sx = x0 + (k % per_row) * pitch
            sy = y0 + 26 + (k // per_row) * (slot + label_h + 14)
            slots.append((sx, sy))
            g = [f'<rect x="{sx}" y="{sy}" width="{slot}" height="{slot}" rx="10" fill="{VELVET}" stroke="{VIOLET}" stroke-opacity=".45"/>',
                 f'<rect x="{sx + 3}" y="{sy + 3}" width="{slot - 6}" height="{slot - 6}" rx="8" fill="none" stroke="{GOLD}" stroke-opacity=".12"/>',
                 icon(s, ref, sx + slot / 2, sy + slot / 2, 26),
                 s.text(sx + slot / 2, sy + slot + 16, label, "sans", 11.5, LILAC, "middle", weight=500)]
            s.add("".join(g))
    # A selection cursor that hops around the grid like an inventory screen
    picks = slots[::max(1, len(slots) // 9)][:9]
    frames = "".join(f"{i * 100 / len(picks):.1f}%{{transform:translate({x - 4}px,{y - 4}px)}}" for i, (x, y) in enumerate(picks))
    s.css.append(f"@keyframes cur{{{frames}}}")
    s.add(f'<g class="cur"><rect width="{slot + 8}" height="{slot + 8}" rx="13" fill="none" stroke="{GOLD_HI}" stroke-width="2" '
          f'filter="url(#softglow)"/></g>')
    write("inventory", s)


# ── Achievements ──────────────────────────────────────────────────────────
def achievements():
    W, tw, th = 1000, 470, 92
    H = 20 + ((len(ACHIEVEMENTS) + 1) // 2) * 108
    s = Svg(W, H, "Achievements: " + "; ".join(f"{a[1]} ({a[2]})" for a in ACHIEVEMENTS))
    common_defs(s)
    for i, (ico, title, sub, pts) in enumerate(ACHIEVEMENTS):
        x, y = 20 + (i % 2) * 490, 20 + (i // 2) * 108
        delay = .3 + i * .35
        s.defs.append(f'<clipPath id="ac{i}"><rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="46"/></clipPath>')
        toast = [
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="46" fill="{VELVET}" stroke="url(#trim)" stroke-width="1.5"/>',
            f'<circle cx="{x + 46}" cy="{y + 46}" r="32" fill="#0b0716" stroke="{GOLD}" stroke-width="2"/>',
            sprite(ico, x + 28, y + 28, 4, "url(#goldV)", extra='filter="url(#softglow)"'),
            s.text(x + 92, y + 30, "ACHIEVEMENT UNLOCKED", size=9, fill=VIOLET_HI),
            s.text(x + 92, y + 56, title, "sans", 18, GOLD_HI, weight=700),
            s.text(x + 92, y + 76, sub, "sans", 13, MUTED, weight=500),
            s.text(x + tw - 26, y + 56, pts, size=12, fill=GOLD, anchor="end"),
            f'<rect x="{x - 140}" y="{y}" width="120" height="{th}" fill="url(#shine)" clip-path="url(#ac{i})">'
            f'<animate attributeName="x" values="{x - 140};{x + tw + 20};{x + tw + 20}" keyTimes="0;.25;1" '
            f'dur="6s" begin="{delay + .6:.2f}s" repeatCount="indefinite"/></rect>',
        ]
        s.add("".join(toast))
    write("achievements", s)


# ── Scoreboard (live GitHub stats) ────────────────────────────────────────
STATS_QUERY = """query($login:String!){user(login:$login){
  followers{totalCount}
  repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount
    nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
  contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions
    contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch_stats():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": STATS_QUERY, "variables": {"login": OWNER}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "arcade-readme"})
    user = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]
    cc = user["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current, tail = 0, counts[:-1] if counts and counts[-1] == 0 else counts
    for c in reversed(tail):
        if not c:
            break
        current += 1
    langs = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    tot = sum(v for _, v in top) or 1
    return {
        "updated": dt.date.today().isoformat(),
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "repos": user["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "followers": user["followers"]["totalCount"],
        "current_streak": current,
        "longest_streak": longest,
        "weeks": [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cc["contributionCalendar"]["weeks"]],
        "languages": [[n, round(v * 100 / tot, 1)] for n, v in top],
    }


def load_stats():
    try:
        stats = fetch_stats()
        if stats:
            with open(STATS_CACHE, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=1)
            return stats
    except Exception as exc:  # keep building with cached numbers
        print("  ! stats fetch failed:", exc)
    if os.path.exists(STATS_CACHE):
        return json.load(open(STATS_CACHE, encoding="utf-8"))
    return None


def days(n):
    if n is None:
        return "-- DAYS"
    return f"{n} DAY" if n == 1 else f"{n} DAYS"


def scoreboard():
    st = load_stats()
    W, H = 1000, 420
    s = Svg(W, H, "GitHub stats" + (f": {st['contributions']} contributions in the last year, "
                                    f"{st['current_streak']}-day current streak" if st else ""))
    common_defs(s)
    frame(s, W, H)
    overlay = crt(s, 24, 24, W - 48, H - 48, 18)

    def val(key):
        return f"{st[key]:,}" if st else "------"

    s.add(s.text(60, 70, "HIGH SCORES", size=15, fill=GOLD, extra='filter="url(#softglow)"'))
    s.add(s.text(W - 60, 70, f"SYNCED {st['updated']}" if st else "SYNCING WITH GITHUB…", size=9, fill=MUTED, anchor="end"))
    rows = [("1ST", "CONTRIBUTIONS · 12 MO", "contributions"), ("2ND", "COMMITS", "commits"),
            ("3RD", "PULL REQUESTS", "prs"), ("4TH", "PUBLIC REPOS", "repos"),
            ("5TH", "STARS EARNED", "stars"), ("6TH", "FOLLOWERS", "followers")]
    for i, (rank, label, key) in enumerate(rows):
        y = 108 + i * 30
        col = GOLD if i == 0 else (VIOLET_HI if i < 3 else LILAC)
        g = [s.text(60, y, rank, size=12, fill=col),
             s.text(120, y, label, size=12, fill=col),
             s.text(520, y, val(key), size=12, fill=col, anchor="end")]
        s.add("".join(g))
        s.add(f'<line x1="{120 + len(label) * 12 + 10}" y1="{y - 4}" x2="{510 - len(val(key)) * 12}" y2="{y - 4}" '
              f'stroke="{MUTED}" stroke-opacity=".5" stroke-dasharray="2 6"/>')

    # Streak panel
    px = 580
    s.add(f'<rect x="{px}" y="86" width="360" height="190" rx="14" fill="#0b0716" stroke="{GOLD_LO}" stroke-opacity=".6"/>')
    s.add(f'<g class="flicker" style="animation-duration:1.4s">{sprite("flame", px + 26, 112, 7, "url(#goldV)", extra="filter=\"url(#softglow)\"")}</g>')
    s.add(s.text(px + 110, 124, "CURRENT STREAK", size=10, fill=VIOLET_HI))
    s.add(s.text(px + 110, 168, days(st and st["current_streak"]), size=26, fill="url(#goldV)",
                 extra='filter="url(#softglow)"'))
    s.add(s.text(px + 110, 200, "LONGEST", size=10, fill=MUTED))
    s.add(s.text(px + 340, 200, days(st and st["longest_streak"]), size=10, fill=LILAC, anchor="end"))
    langs = st["languages"] if st else []
    s.add(s.text(px + 20, 234, "TOP LANGS", size=9, fill=MUTED))
    lx = px + 120
    lcols = [GOLD, VIOLET, PHOSPHOR, VIOLET_HI, GOLD_LO]
    for k, (name, pct) in enumerate(langs):
        wseg = 220 * pct / 100
        s.add(f'<rect x="{lx:.1f}" y="226" width="{max(wseg - 2, 1):.1f}" height="10" fill="{lcols[k]}"/>')
        lx += wseg
    if langs:
        legend = "  ".join(f"{n} {p:g}%" for n, p in langs[:3])
        s.add(s.text(px + 340, 262, legend, "sans", 11, LILAC, "end", weight=500))

    # 52-week activity bars
    weeks = st["weeks"][-52:] if st else [0] * 52
    peak = max(weeks) or 1
    bx, by, bw, bh = 60, 370, 880, 72
    s.add(s.text(60, 290, "ACTIVITY · LAST 52 WEEKS", size=9, fill=MUTED))
    step = bw / len(weeks)
    for k, v in enumerate(weeks):
        h = max(2, bh * v / peak)
        col = GOLD if v == peak and v else VIOLET
        s.add(f'<rect x="{bx + k * step:.1f}" y="{by - h:.1f}" width="{step - 4:.1f}" height="{h:.1f}" rx="2" fill="{col}" '
              f'opacity="{.45 + .55 * v / peak:.2f}"/>')
    s.add(f'<line x1="{bx}" y1="{by + 1}" x2="{bx + bw}" y2="{by + 1}" stroke="{GOLD}" stroke-opacity=".3"/>')
    s.add(overlay)
    write("scoreboard", s)


# ── Side quests ───────────────────────────────────────────────────────────
def side_quests():
    W, H, tw = 1000, 196, 232
    s = Svg(W, H, "Side quests: " + "; ".join(f"{q[1]}: {q[2]}" for q in SIDE_QUESTS))
    common_defs(s)
    s.css.append(".hop{animation:hop 2.8s ease-in-out infinite}@keyframes hop{50%{transform:translateY(-4px)}}")
    for i, (ico, title, line) in enumerate(SIDE_QUESTS):
        x = 12 + i * (tw + 13)
        s.add(f'<rect x="{x}" y="6" width="{tw}" height="184" rx="16" fill="{VELVET}" stroke="{GOLD_LO}" stroke-opacity=".6"/>')
        s.add(f'<rect x="{x}" y="6" width="{tw}" height="184" rx="16" fill="url(#scan)" opacity=".6"/>')
        glow = 'filter="url(#softglow)"'
        s.add(f'<g class="hop" style="animation-delay:-{i * .7:.1f}s">{sprite(ico, x + tw / 2 - 22.5, 28, 5, "url(#goldV)", extra=glow)}</g>')
        s.add(s.text(x + tw / 2, 106, title, size=13, fill=GOLD, anchor="middle"))
        for k, ln in enumerate(wrap(line, tw - 36, "sans", 13.5, 400)):
            s.add(s.text(x + tw / 2, 136 + k * 20, ln, "sans", 13.5, LILAC, "middle", weight=400))
    write("side-quests", s)


# ── Contact buttons ───────────────────────────────────────────────────────
def button(name, label, ref, primary):
    W, H = 240, 64
    s = Svg(W, H, label.title())
    common_defs(s)
    s.defs.append(f'<clipPath id="bc"><rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="12"/></clipPath>')
    fg = INK if primary else GOLD_HI
    s.add(f'<rect x="2" y="5" width="{W - 4}" height="{H - 6}" rx="13" fill="{GOLD_LO if primary else "#05030b"}"/>')
    s.add(f'<rect x="2" y="2" width="{W - 4}" height="{H - 8}" rx="13" fill="{"url(#goldV)" if primary else VELVET}" '
          f'stroke="{GOLD if not primary else GOLD_HI}" stroke-width="1.5"/>')
    if not primary:
        s.add(f'<rect x="2" y="2" width="{W - 4}" height="{H - 8}" rx="13" fill="url(#scan)" opacity=".6"/>')
    s.add(icon(s, ref, 38, 30, 24, INK if primary else GOLD))
    s.add(s.text(64, 36, label, size=12, fill=fg))
    s.add(f'<rect x="-80" y="0" width="60" height="{H}" fill="url(#shine)" clip-path="url(#bc)">'
          f'<animate attributeName="x" values="-80;{W + 20};{W + 20}" keyTimes="0;.3;1" dur="5s" '
          f'begin="{sum(map(ord, name)) % 30 / 10:.1f}s" repeatCount="indefinite"/></rect>')
    write(name, s)


# ── Footer: continue screen ───────────────────────────────────────────────
def footer():
    W, H = 1000, 220
    s = Svg(W, H, "Thanks for playing. Insert coin to continue.")
    common_defs(s)
    frame(s, W, H)
    overlay = crt(s, 24, 24, W - 48, H - 48, 16)
    s.add(s.text(W / 2, 84, "Thanks for playing", "serif", 40, "url(#gold)", "middle", 'filter="url(#softglow)"'))
    s.add(s.text(W / 2 - 40, 132, "CONTINUE?", size=18, fill=LILAC, anchor="middle"))
    n = 10
    glow = 'filter="url(#softglow)"'
    for k in range(n):
        vals = ";".join("1" if j == k else "0" for j in range(n + 2))
        s.add(f'<g opacity="0"><animate attributeName="opacity" values="{vals}" calcMode="discrete" dur="{n + 2}s" '
              f'repeatCount="indefinite"/>{s.text(W / 2 + 112, 134, str(9 - k), size=26, fill=RED, anchor="middle", extra=glow)}</g>')
    vals = ";".join("1" if j >= n else "0" for j in range(n + 2))
    s.add(f'<g opacity="0"><animate attributeName="opacity" values="{vals}" calcMode="discrete" dur="{n + 2}s" repeatCount="indefinite"/>'
          f'{s.text(W / 2 + 112, 134, "★", size=26, fill=GOLD, anchor="middle")}</g>')
    s.add(f'<g class="blink">{s.text(W / 2, 172, "INSERT COIN · HIRE PLAYER ONE", size=12, fill=GOLD, anchor="middle")}</g>')
    s.add(overlay)
    write("footer", s)


if __name__ == "__main__":
    print("Building assets →", OUT)
    hero()
    ticker()
    divider()
    for name, (label, title) in STAGES.items():
        stage_header(name, label, title)
    player()
    quest_log()
    level_select()
    inventory()
    achievements()
    scoreboard()
    side_quests()
    for b in BUTTONS:
        button(*b)
    footer()
