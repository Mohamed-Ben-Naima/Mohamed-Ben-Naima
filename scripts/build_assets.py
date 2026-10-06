#!/usr/bin/env python3
"""Build the arcade-themed SVGs used by the profile README.

Every image lives in ../assets and is fully self-contained: fonts are
subset to the glyphs each file uses and embedded as WOFF2, animations are
SMIL/CSS only (GitHub strips scripts), so they render the same everywhere.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Fonts (both SIL OFL) are downloaded once into scripts/.fonts/.
Edit the CONTENT section below to change text, skills or projects.
"""

import base64
import io
import os
import urllib.request
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
FONT_DIR = os.path.join(ROOT, "scripts", ".fonts")
FONT_SRC = {
    "pixel": "https://raw.githubusercontent.com/google/fonts/main/ofl/pressstart2p/PressStart2P-Regular.ttf",
    "serif": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
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
MUTED = "#8a7bb8"
PHOSPHOR = "#5eead4"   # used sparingly: CRT glow accents

SANS = "'Segoe UI','Helvetica Neue',system-ui,-apple-system,sans-serif"

# ── CONTENT ───────────────────────────────────────────────────────────────
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

PROJECTS = [  # title, world, icon, description lines, tech, badge, status
    ("Secured Banking Infra", "WORLD 1-1", "bank",
     ["Microservices banking app on a private OpenStack",
      "cloud: dual pfSense, VLANs, Kafka, KYC and",
      "full observability."],
     ["Spring Boot", "Angular", "Kafka", "GNS3"], "★ NOMINEE", "CLEARED"),
    ("Hermes Suite", "WORLD 1-2", "doc",
     ["Reporting & invoicing dashboard: revenue,",
      "orders, top sellers, PDF invoices. Evolving",
      "into a multi-tenant SaaS."],
     ["React", "Express", "MongoDB", "Render"], None, "IN PROGRESS"),
    ("The Hive", "WORLD 2-1", "bolt",
     ["Authenticated REST backend for a trading",
      "platform: JWT + OAuth2, OpenAPI docs and",
      "Postman test suites."],
     ["FastAPI", "JWT", "OAuth2", "OpenAPI"], None, "CLEARED"),
    ("MiraviaSpace", "WORLD 2-2", "globe",
     ["Travel & social platform (team of 6). Owned",
      "the whole client side, including an in-house",
      "AI chatbot."],
     ["Symfony", "Oracle", "JavaFX", "AI"], "★ RUNNER-UP", "CLEARED"),
]

ACHIEVEMENTS = [  # icon, title, subtitle, points
    ("trophy", "Bal de Projet · Nominee", "Secured Banking Infrastructure", "100G"),
    ("medal", "Bal de Projet · Runner-up", "MiraviaSpace, team of six", "75G"),
    ("rocket", "Shipped to Production", "Microtiss Confect ERP & Hermes Suite", "150G"),
    ("shield", "Box Breaker", "Hacking rooms & CTFs on TryHackMe", "50G"),
]

SIDE_QUESTS = [  # icon, title, line
    ("dumbbell", "GYM", "Discipline, in the terminal and out of it."),
    ("knight", "CHESS", "Thinking moves ahead, like hunting edge cases."),
    ("book", "BOOKS", "Security, systems and the odd page of fiction."),
    ("glove", "KICKBOXING", "Problem-solving with solid form."),
]

STAGES = {  # file: (stage label, title)
    "h-player": ("STAGE 01 · PLAYER SELECT", "The Player"),
    "h-stack": ("STAGE 02 · INVENTORY", "Tech Arsenal"),
    "h-projects": ("STAGE 03 · LEVEL SELECT", "Featured Work"),
    "h-trophies": ("STAGE 04 · ACHIEVEMENTS", "Hall of Fame"),
    "h-stats": ("STAGE 05 · SCOREBOARD", "GitHub Stats"),
    "h-snake": ("STAGE 06 · BONUS ROUND", "Contribution Arcade"),
    "h-beyond": ("STAGE 07 · SIDE QUESTS", "Beyond the Code"),
}

# ── Pixel sprites (X = filled; letters map to palette in sprite()) ───────
SPRITES = {
    "invader_a": ["..X.....X..", "...X...X...", "..XXXXXXX..", ".XX.XXX.XX.",
                  "XXXXXXXXXXX", "X.XXXXXXX.X", "X.X.....X.X", "...XX.XX..."],
    "invader_b": ["..X.....X..", "X..X...X..X", "X.XXXXXXX.X", "XXX.XXX.XXX",
                  "XXXXXXXXXXX", ".XXXXXXXXX.", "..X.....X..", ".X.......X."],
    "ghost": ["...XXXX...", ".XXXXXXXX.", "XXXXXXXXXX", "XX..XX..XX", "XX..XX..XX",
              "XXXXXXXXXX", "XXXXXXXXXX", "XXXXXXXXXX", "XX.XX.XX.X", "X...X...X."],
    "bank": ["....X....", "..XXXXX..", "XXXXXXXXX", ".........", ".X.X.X.X.",
             ".X.X.X.X.", ".X.X.X.X.", ".........", "XXXXXXXXX"],
    "doc": ["XXXXXX...", "X....XX..", "X.XX.XXX.", "X......X.", "X.XXXX.X.",
            "X......X.", "X.XXXX.X.", "X......X.", "XXXXXXXX."],
    "bolt": [".....XXX.", "....XXX..", "...XXX...", "..XXXXXX.", "....XXX..",
             "...XXX...", "..XX.....", ".XX......", "X........"],
    "globe": ["..XXXXX..", ".X..X..X.", "X..X.X..X", "XXXXXXXXX", "X..X.X..X",
              "X..X.X..X", "XXXXXXXXX", ".X..X..X.", "..XXXXX.."],
    "trophy": ["XXXXXXXXX", "XXXXXXXXX", "X.XXXXX.X", "X.XXXXX.X", ".XXXXXXX.",
               "..XXXXX..", "...XXX...", "....X....", "..XXXXX.."],
    "medal": ["XX.....XX", ".XX...XX.", "..XX.XX..", "...XXX...", "..XXXXX..",
              ".XXX.XXX.", ".XX...XX.", ".XXX.XXX.", "..XXXXX.."],
    "rocket": ["....X....", "...XXX...", "...X.X...", "...XXX...", "...XXX...",
               "..XXXXX..", ".XX.X.XX.", "X...X...X", "...X.X..."],
    "shield": ["XXXXXXXXX", "X...X...X", "X...X...X", "XXXXXXXXX", "X...X...X",
               ".X..X..X.", ".X..X..X.", "..X.X.X..", "....X...."],
    "dumbbell": [".........", ".X.....X.", "XX.....XX", "XX.....XX", "XXXXXXXXX",
                 "XX.....XX", "XX.....XX", ".X.....X.", "........."],
    "knight": ["...XX....", "..XXXX...", ".XX.XXX..", "XXXXXXXX.", "....XXX..",
               "...XXXX..", "..XXXXX..", ".XXXXXXX.", ".XXXXXXX."],
    "book": ["XXXX.XXXX", "X..XXX..X", "X..XXX..X", "X..XXX..X", "X..XXX..X",
             "X..XXX..X", "XXXXXXXXX", "....X....", "........."],
    "glove": ["..XXXXX..", ".XXXXXXX.", ".XXXXXXXX", ".XXXXXXXX", ".XXXXXXX.",
              ".XXXXXXX.", "..XXXXX..", "..XXXXX..", "..XXXXX.."],
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


# ── Font embedding ────────────────────────────────────────────────────────
def font_path(key):
    os.makedirs(FONT_DIR, exist_ok=True)
    path = os.path.join(FONT_DIR, key + ".ttf")
    if not os.path.exists(path):
        urllib.request.urlretrieve(FONT_SRC[key], path)
    return path


def woff2(key, chars):
    font = TTFont(font_path(key))
    if "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": 700})
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


class Svg:
    """Collects markup and the glyphs used per embedded font."""

    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.parts, self.defs, self.css = [], [], []
        self.glyphs = {"pixel": set(), "serif": set()}

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, font="pixel", size=12, fill=GOLD, anchor="start",
             extra="", inner="", weight=700):
        family = {"pixel": "PX,'Courier New',monospace",
                  "serif": "PF,'Playfair Display',Georgia,serif",
                  "sans": SANS}[font]
        if font in self.glyphs:
            self.glyphs[font].update(s)
        weight = f' font-weight="{weight}"' if font != "pixel" else ""
        return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}"{weight} '
                f'fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}{inner}</text>')

    def render(self):
        faces = []
        for key, fam in (("pixel", "PX"), ("serif", "PF")):
            if self.glyphs[key]:
                faces.append(f"@font-face{{font-family:{fam};src:url(data:font/woff2;base64,"
                             f"{woff2(key, self.glyphs[key])}) format('woff2');}}")
        style = "".join(faces) + "".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}">\n'
                f'<style>{style}</style>\n<defs>{"".join(self.defs)}</defs>\n'
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
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#scan)" pointer-events="none"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="#000" stroke-opacity=".6" stroke-width="6"/>'
            f'<path d="M{x + 18} {y + 40} Q{x + 18} {y + 16} {x + 60} {y + 14} L{x + w * .42} {y + 12}" '
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
            d = -((i % 3) * 0.3)
            bulbs.append(f'<circle cx="{bx}" cy="{by}" r="3.2" fill="{GOLD_MID}" class="bulb" '
                         f'style="animation-delay:{d:.1f}s"/>')
    s.add(f'<g filter="url(#softglow)">{"".join(bulbs)}</g>')
    s.add(s.text(W / 2, 69, "★ BEN NAIMA ARCADE ★", size=22, fill="url(#goldV)", anchor="middle",
                 extra='filter="url(#softglow)" letter-spacing="2"'))

    # Screen
    sx, sy, sw, sh = 40, 112, W - 80, 268
    overlay = crt(s, sx, sy, sw, sh)
    g = []
    g.append(s.text(72, 148, "1UP", fill="#ff5d73", extra='class="blink"'))
    g.append(s.text(72, 166, "MOHAMED", fill=LILAC))
    g.append(s.text(W / 2, 148, "HI-SCORE", fill="#ff5d73", anchor="middle"))
    g.append(s.text(W / 2, 166, "999999", fill=LILAC, anchor="middle"))
    g.append(s.text(W - 72, 148, "CREDIT", fill="#ff5d73", anchor="end"))
    g.append(s.text(W - 72, 166, "01", fill=LILAC, anchor="end"))

    # Marching invaders + ghosts
    inv = []
    for i, x in enumerate(range(250, 640, 64)):
        col = GOLD if i % 2 == 0 else VIOLET_HI
        inv.append(f'<g class="fa">{sprite("invader_a", x, 184, 3, col)}</g>'
                   f'<g class="fb">{sprite("invader_b", x, 184, 3, col)}</g>')
    g.append(f'<g class="march" opacity=".9">{"".join(inv)}</g>')

    # Name with glow + shimmer
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
    # Player sprite peeking bottom-right
    g.append(f'<g class="bob">{sprite("hero", 820, 186, 4, palette=HERO_PALETTE)}</g>')
    g.append(f'<g class="bob" style="animation-delay:-1.2s">{sprite("ghost", 120, 196, 4, "#ff5d73")}'
             f'<rect x="128" y="208" width="4" height="4" fill="#fff"/><rect x="144" y="208" width="4" height="4" fill="#fff"/></g>')
    s.add(f'<g class="flicker">{"".join(g)}</g>')
    s.add(overlay)

    # Control deck
    s.add(f'<rect x="22" y="392" width="{W - 44}" height="48" rx="12" fill="#100a22" stroke="{GOLD_LO}" stroke-opacity=".6"/>')
    s.add(f'<rect x="90" y="413" width="44" height="8" rx="4" fill="#05030b"/>'
          f'<line x1="112" y1="417" x2="112" y2="400" stroke="#cfc6e6" stroke-width="4" stroke-linecap="round">'
          f'<animateTransform attributeName="transform" type="rotate" values="0 112 417;-18 112 417;0 112 417;18 112 417;0 112 417" dur="4s" repeatCount="indefinite"/></line>'
          f'<circle cx="112" cy="400" r="8" fill="{VIOLET}"><animateTransform attributeName="transform" type="rotate" '
          f'values="0 112 417;-18 112 417;0 112 417;18 112 417;0 112 417" dur="4s" repeatCount="indefinite"/></circle>')
    for i, (bx, col) in enumerate(((W - 200, GOLD), (W - 160, VIOLET_HI), (W - 120, "#ff5d73"))):
        s.add(f'<circle cx="{bx}" cy="416" r="11" fill="#05030b"/>'
              f'<circle cx="{bx}" cy="414" r="10" fill="{col}"><animate attributeName="cy" values="414;416;414;414" '
              f'keyTimes="0;.05;.1;1" dur="3s" begin="{i * .4}s" repeatCount="indefinite"/></circle>')
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


# ── Dividers & stage headers ──────────────────────────────────────────────
def divider():
    W, H = 1000, 30
    s = Svg(W, H, "divider")
    common_defs(s)
    dots = "".join(
        f'<rect x="{x}" y="13" width="4" height="4" fill="{GOLD}" opacity=".55">'
        f'<animate attributeName="opacity" values=".55;.55;0;0;.55" keyTimes="0;{(x - 40) / 950 * .8:.3f};{(x - 40) / 950 * .8 + .01:.3f};.95;1" '
        f'dur="8s" repeatCount="indefinite"/></rect>'
        for x in range(40, 961, 28))
    s.add(dots)
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
    pw = 420
    x0 = (W - pw) / 2
    s.add(f'<line x1="40" y1="52" x2="{x0 - 14}" y2="52" stroke="url(#fadeL)"/>'
          f'<line x1="{x0 + pw + 14}" y1="52" x2="{W - 40}" y2="52" stroke="url(#fadeR)"/>')
    # Chamfered plaque
    c = 12
    s.add(f'<path d="M{x0 + c} 8h{pw - 2 * c}l{c} {c}v{H - 16 - 2 * c}l-{c} {c}h-{pw - 2 * c}l-{c} -{c}v-{H - 16 - 2 * c}z" '
          f'fill="{VELVET}" stroke="url(#trim)" stroke-width="1.6"/>')
    s.add(f'<path d="M{x0 + c} 8h{pw - 2 * c}l{c} {c}v{H - 16 - 2 * c}l-{c} {c}h-{pw - 2 * c}l-{c} -{c}v-{H - 16 - 2 * c}z" fill="url(#scan)"/>')
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

    # Portrait
    overlay = crt(s, 26, 26, 300, 348, 16)
    s.add(f'<ellipse cx="176" cy="212" rx="90" ry="14" fill="{VIOLET}" opacity=".25" filter="url(#glow)"/>')
    s.add(f'<g class="bob">{sprite("hero", 112, 72, 8, palette=HERO_PALETTE)}'
          f'<g class="blink" style="animation-duration:3.2s">'
          f'<rect x="152" y="112" width="8" height="8" fill="#0a0716"/><rect x="176" y="112" width="8" height="8" fill="#0a0716"/></g>'
          f'<rect x="136" y="184" width="80" height="8" fill="{PHOSPHOR}" opacity=".35" class="pulse"/></g>')
    s.add(s.text(176, 262, "MOHAMED", size=18, fill="url(#goldV)", anchor="middle", extra='filter="url(#softglow)"'))
    s.add(s.text(176, 288, "CLASS: SEC-DEV", size=11, fill=LILAC, anchor="middle"))
    s.add(s.text(176, 308, "ORIGIN: MAHDIA, TN", size=11, fill=MUTED, anchor="middle"))
    s.add(f'<g class="blink">{s.text(176, 346, "P1 READY", size=12, fill=PHOSPHOR, anchor="middle")}</g>')
    s.add(overlay)

    # Attributes
    s.add(s.text(360, 56, "ATTRIBUTES", size=14, fill=GOLD))
    s.add(f'<line x1="360" y1="68" x2="{W - 30}" y2="68" stroke="{GOLD}" stroke-opacity=".25"/>')
    segs, bx, bw = 20, 560, 340
    sw = bw / segs
    for i, (label, val, rank) in enumerate(ATTRIBUTES):
        y = 98 + i * 36
        s.add(s.text(360, y + 11, label, size=11, fill=LILAC))
        s.add(f'<rect x="{bx}" y="{y}" width="{bw}" height="14" fill="#0b0716" stroke="{GOLD_LO}" stroke-opacity=".5"/>')
        fill = bw * val / 100
        s.add(f'<rect x="{bx}" y="{y}" width="{fill:.1f}" height="14" fill="url(#gold)">'
              f'<animate attributeName="width" from="0" to="{fill:.1f}" dur="1.2s" begin="{.3 + i * .18:.2f}s" fill="freeze" '
              f'calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/></rect>')
        s.add("".join(f'<rect x="{bx + k * sw - 1:.1f}" y="{y}" width="2" height="14" fill="#0b0716"/>' for k in range(1, segs)))
        rank_col = GOLD if rank == "S" else VIOLET_HI
        s.add(s.text(bx + bw + 22, y + 13, rank, size=14, fill=rank_col, extra='filter="url(#softglow)"'))

    # Quest + special moves
    qy = 330
    s.add(s.text(360, qy - 14, "CURRENT QUEST", size=10, fill=VIOLET_HI))
    s.add(s.text(360, qy + 6, "Land a PFE internship", "serif", 20, "url(#gold)"))
    s.add(f'<rect x="{bx + 60}" y="{qy - 6}" width="{bw - 60}" height="10" rx="5" fill="#0b0716" stroke="{VIOLET}" stroke-opacity=".6"/>'
          f'<rect x="{bx + 60}" y="{qy - 6}" width="{(bw - 60) * .85:.0f}" height="10" rx="5" fill="{VIOLET}" class="pulse"/>')
    s.add(s.text(bx + bw + 22, qy + 4, "XP", size=10, fill=VIOLET_HI))
    s.add(s.text(360, qy + 36, "SPECIAL MOVES: ERPs THAT SHIP · BREAK & HARDEN · CTFs", size=9, fill=MUTED))
    write("player", s)


# ── Level select (projects) ───────────────────────────────────────────────
def level_select():
    W, H = 1000, 600
    s = Svg(W, H, "Featured projects: " + "; ".join(p[0] for p in PROJECTS))
    common_defs(s)
    s.css.append(".sel{animation:sel 10s steps(1) infinite}"
                 "@keyframes sel{0%{transform:translate(0,0)}25%{transform:translate(488px,0)}"
                 "50%{transform:translate(0,282px)}75%{transform:translate(488px,282px)}}")
    frame(s, W, H)
    cw, ch = 462, 262
    for i, (title, world, icon, desc, tech, badge, status) in enumerate(PROJECTS):
        x = 26 + (i % 2) * 488
        y = 26 + (i // 2) * 282
        # Cartridge silhouette: notched top corners + grip ridges
        s.add(f'<path d="M{x + 18} {y}h{cw - 36}l18 18v{ch - 18}h-{cw}v-{ch - 18}z" fill="{VELVET}" stroke="{GOLD_LO}" stroke-opacity=".55"/>')
        s.add("".join(f'<rect x="{x + cw / 2 - 60 + k * 16}" y="{y + 8}" width="8" height="3" rx="1.5" fill="{GOLD}" opacity=".35"/>'
                      for k in range(8)))
        # Label plate
        s.add(f'<rect x="{x + 16}" y="{y + 22}" width="{cw - 32}" height="{ch - 38}" rx="8" fill="url(#screen)"/>')
        s.add(f'<rect x="{x + 16}" y="{y + 22}" width="{cw - 32}" height="{ch - 38}" rx="8" fill="url(#scan)" opacity=".7"/>')
        s.add(f'<rect x="{x + 30}" y="{y + 38}" width="44" height="44" rx="8" fill="#0b0716" stroke="{GOLD}" stroke-opacity=".5"/>')
        s.add(sprite(icon, x + 34.5, y + 42.5, 4, GOLD, extra='filter="url(#softglow)"'))
        s.add(s.text(x + 88, y + 52, world, size=9, fill=VIOLET_HI))
        s.add(s.text(x + 88, y + 78, title, "serif", 23, "url(#gold)"))
        if badge:
            bw = len(badge) * 9 + 18
            s.add(f'<rect x="{x + cw - 30 - bw}" y="{y + 38}" width="{bw}" height="20" rx="3" fill="{GOLD}"/>')
            s.add(s.text(x + cw - 30 - bw / 2, y + 52, badge, size=9, fill=INK, anchor="middle"))
        for k, line in enumerate(desc):
            s.add(s.text(x + 30, y + 112 + k * 21, line, "sans", 14, LILAC, weight=400))
        cx = x + 30
        for t in tech:
            tw = len(t) * 7.4 + 18
            s.add(f'<rect x="{cx}" y="{y + 186}" width="{tw:.0f}" height="22" rx="11" fill="none" stroke="{VIOLET}" stroke-opacity=".8"/>')
            s.add(s.text(cx + tw / 2, y + 201, t, "sans", 12, VIOLET_HI, "middle"))
            cx += tw + 8
        st_col = PHOSPHOR if status == "CLEARED" else GOLD
        s.add(s.text(x + 30, y + 236, "STATUS:", size=9, fill=MUTED))
        s.add(f'<g class="{"" if status == "CLEARED" else "blink"}">'
              f'{s.text(x + 100, y + 236, status, size=9, fill=st_col)}</g>')
    # Animated selection cursor hopping between cartridges
    s.add(f'<g class="sel"><path d="M18 18h40M18 18v40 M{18 + cw + 16} 18h-40M{18 + cw + 16} 18v40 '
          f'M18 {18 + ch + 16}h40M18 {18 + ch + 16}v-40 M{18 + cw + 16} {18 + ch + 16}h-40M{18 + cw + 16} {18 + ch + 16}v-40" '
          f'stroke="{GOLD_HI}" stroke-width="3" fill="none" filter="url(#softglow)" class="blink" style="animation-duration:.8s"/></g>')
    write("level-select", s)


# ── Achievements ──────────────────────────────────────────────────────────
def achievements():
    W, H = 1000, 236
    s = Svg(W, H, "Achievements: " + "; ".join(f"{a[1]} ({a[2]})" for a in ACHIEVEMENTS))
    common_defs(s)
    s.css.append(".toast{animation:toast .6s ease-out backwards}"
                 "@keyframes toast{from{opacity:0;transform:translateY(14px)}}")
    tw, th = 470, 92
    for i, (icon, title, sub, pts) in enumerate(ACHIEVEMENTS):
        x = 20 + (i % 2) * 490
        y = 20 + (i // 2) * 108
        delay = .3 + i * .45
        s.defs.append(f'<clipPath id="ac{i}"><rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="46"/></clipPath>')
        toast = [
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="46" fill="{VELVET}" stroke="url(#trim)" stroke-width="1.5"/>',
            f'<circle cx="{x + 46}" cy="{y + 46}" r="32" fill="#0b0716" stroke="{GOLD}" stroke-width="2"/>',
            sprite(icon, x + 28, y + 28, 4, "url(#goldV)", extra='filter="url(#softglow)"'),
            s.text(x + 92, y + 30, "ACHIEVEMENT UNLOCKED", size=9, fill=VIOLET_HI),
            s.text(x + 92, y + 56, title, "sans", 18, GOLD_HI),
            s.text(x + 92, y + 76, sub, "sans", 13, MUTED, weight=400),
            s.text(x + tw - 26, y + 56, pts, size=12, fill=GOLD, anchor="end"),
            f'<rect x="{x - 140}" y="{y}" width="120" height="{th}" fill="url(#shine)" clip-path="url(#ac{i})">'
            f'<animate attributeName="x" values="{x - 140};{x + tw + 20};{x + tw + 20}" keyTimes="0;.25;1" '
            f'dur="6s" begin="{delay + .6:.2f}s" repeatCount="indefinite"/></rect>',
        ]
        s.add(f'<g class="toast" style="animation-delay:{delay:.2f}s">{"".join(toast)}</g>')
    write("achievements", s)


# ── Side quests ───────────────────────────────────────────────────────────
def side_quests():
    W, H = 1000, 196
    s = Svg(W, H, "Side quests: " + "; ".join(f"{q[1]}: {q[2]}" for q in SIDE_QUESTS))
    common_defs(s)
    s.css.append(".hop{animation:hop 2.8s ease-in-out infinite}@keyframes hop{50%{transform:translateY(-4px)}}")
    tw = 232
    for i, (icon, title, line) in enumerate(SIDE_QUESTS):
        x = 12 + i * (tw + 13)
        s.add(f'<rect x="{x}" y="6" width="{tw}" height="184" rx="16" fill="{VELVET}" stroke="{GOLD_LO}" stroke-opacity=".6"/>')
        s.add(f'<rect x="{x}" y="6" width="{tw}" height="184" rx="16" fill="url(#scan)" opacity=".6"/>')
        s.add(f'<g class="hop" style="animation-delay:-{i * .7:.1f}s">'
              f'{sprite(icon, x + tw / 2 - 22.5, 28, 5, "url(#goldV)", extra="filter=\"url(#softglow)\"")}</g>')
        s.add(s.text(x + tw / 2, 106, title, size=13, fill=GOLD, anchor="middle"))
        words, lines, cur = line.split(), [], ""
        for w_ in words:
            if len(cur) + len(w_) + 1 > 28:
                lines.append(cur)
                cur = w_
            else:
                cur = (cur + " " + w_).strip()
        lines.append(cur)
        for k, ln in enumerate(lines):
            s.add(s.text(x + tw / 2, 136 + k * 19, ln, "sans", 13, LILAC, "middle", weight=400))
    write("side-quests", s)


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
    for k in range(n):
        vals = ";".join("1" if j == k else "0" for j in range(n + 2))
        s.add(f'<g opacity="0"><animate attributeName="opacity" values="{vals}" calcMode="discrete" dur="{n + 2}s" '
              f'repeatCount="indefinite"/>{s.text(W / 2 + 112, 134, str(9 - k), size=26, fill="#ff5d73", anchor="middle", extra="filter=\"url(#softglow)\"")}</g>')
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
    level_select()
    achievements()
    side_quests()
    footer()
