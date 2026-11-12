"""Build the SVG cards used in the profile README.

Static cards come from the data below; the events and stats cards are
rebuilt from the GDG chapter API and the GitHub GraphQL API.
Run from anywhere:  python .github/scripts/build_cards.py
"""
import base64
import datetime
import html
import json
import math
import os
import re
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, "assets")
SRC = os.path.join(ASSETS, "src")
USER = "Timujaponya"
GDG_CHAPTER = 3497

W = 840
# Banner theme: orange -> purple gradient, white type, dark glass panels.
C = dict(bg="#16150f", card="rgba(22,21,15,.28)", line="rgba(255,255,255,.22)", ink="#ffffff",
         ink2="rgba(255,255,255,.86)", ink3="rgba(255,255,255,.66)",
         acc="#ffd9c9", game="#e2daff", game_d="#6c4cf5", lime="#d4ff6b", green="#d4ff6b",
         g1="#ff5a1f", g2="#c2452f", g3="#6c4cf5")
SANS = "'Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
MONO = "Consolas,'SFMono-Regular',Menlo,'Courier New',monospace"
SERIF = "Georgia,'Times New Roman',serif"


# ---------- helpers ----------
def esc(s):
    return html.escape(str(s), quote=True)


def width(t, size, k=0.53):
    return len(t) * size * k


def wrap(t, maxw, size, k=0.53):
    lines, cur = [], ""
    for w in t.split():
        nxt = (cur + " " + w).strip()
        if cur and width(nxt, size, k) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines


def text(x, y, t, size=14, fill=C["ink"], weight=400, font=SANS, anchor="start", ls=0, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}" {extra}>{esc(t)}</text>')


def lines_at(x, y, lines, size=13, gap=1.45, **kw):
    return "".join(text(x, y + i * size * gap, ln, size=size, **kw) for i, ln in enumerate(lines))


def diamond(cx, cy, s, fill, extra=""):
    return f'<rect x="{cx - s / 2:.1f}" y="{cy - s / 2:.1f}" width="{s}" height="{s}" fill="{fill}" transform="rotate(45 {cx:.1f} {cy:.1f})" {extra}/>'


def pill(x, y, label, color, anchor="end", size=10):
    w = len(label) * size * 0.66 + 20
    x0 = x - w if anchor == "end" else x
    return (f'<rect x="{x0:.1f}" y="{y - 14}" width="{w:.1f}" height="20" rx="10" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-opacity=".55"/>'
            + text(x0 + w / 2, y + 0.5, label, size=size, fill=color, weight=700, font=MONO, anchor="middle", ls=1.5))


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


CARDS = []
ORDER = ["about.svg", "now.svg", "featured.svg", "game.svg", "services.svg", "events.svg", "stack.svg", "stats.svg"]
SEAM, AMP = 10, 6.5            # wave depth at each seam
SEAM_PHASES = [0.0, 1.9, 3.7, 0.8, 2.6, 4.4, 1.3, 5.1]


def card(name, h, title, sub, body, accent=C["acc"], aria=""):
    # register only; render_all() draws every card as one continuous strip
    CARDS.append(dict(name=name, h=h + 22, title=title, sub=sub, body=body, accent=accent, aria=aria))


def _wave(base, phase):
    k = 2 * math.pi * 1.25 / W
    return [(x, base + AMP * math.sin(phase + k * x)) for x in range(0, W + 1, 20)]


def _catmull(pts):
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d


def render_all():
    cards = sorted(CARDS, key=lambda c: ORDER.index(c["name"]))
    offs, total = [], 0
    for c in cards:
        offs.append(total)
        total += c["h"]
    # one route and one set of pixels in shared coordinates, so they flow from card to card
    xs = [W - 90, W - 240, W - 120, W - 310, W - 80, W - 200]
    route = _catmull([(xs[j % len(xs)], -40 + j * 230) for j in range(int(total / 230) + 3)])
    pix = []
    for j, y in enumerate(range(120, int(total), 190)):
        x = [W - 250, W - 140, int(W * .47), W - 60, W - 330][j % 5]
        col, op = [("#ffffff", .55), (C["lime"], .8), ("#ffd2c2", .7)][j % 3]
        pix.append((x, y, 7 + j % 3, col, op, -(j % 4) * .7))

    for i, c in enumerate(cards):
        off, h = offs[i], c["h"]
        if i == 0:
            top = f"M0 18Q0 0 18 0H{W - 18}Q{W} 0 {W} 18"
        else:
            tp = _wave(SEAM, SEAM_PHASES[i - 1])
            top = "M" + " L".join(f"{x} {y:.1f}" for x, y in tp)
        bp = _wave(h - SEAM, SEAM_PHASES[i])[::-1]
        shape = top + " L" + " L".join(f"{x} {y:.1f}" for x, y in bp) + "Z"
        tw = width(c["title"], 13, 0.62) + 3 * len(c["title"])
        sw = width(c["sub"], 13, 0.62) + 1 * len(c["sub"])
        line_x = 48 + tw + 12 + sw + 14
        deco = (f'<g transform="translate(0 {-off})">'
                f'<path d="{route}" fill="none" stroke="#ffffff" stroke-opacity=".3" stroke-width="2" stroke-dasharray="2 10" stroke-linecap="round" class="dash"/>'
                + "".join(f'<rect x="{x}" y="{y}" width="{sz}" height="{sz}" rx="1.5" fill="{col}" fill-opacity="{op}" class="bob" style="animation-delay:{dl}s"/>'
                          for x, y, sz, col, op, dl in pix if off - 20 < y < off + h + 20)
                + '</g>')
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{esc(c['aria'] or c['title'])}">
<defs>
<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="translate(0 {-(off % 24)})"><circle cx="2" cy="2" r="1.3" fill="#ffffff" fill-opacity=".16"/></pattern>
<linearGradient id="bgg" gradientUnits="userSpaceOnUse" spreadMethod="reflect" x1="0" y1="{-off}" x2="{W}" y2="{760 - off}"><stop offset="0" stop-color="{C['g1']}"/><stop offset=".5" stop-color="{C['g2']}"/><stop offset="1" stop-color="{C['g3']}"/></linearGradient>
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#ffffff" stop-opacity=".5"/></linearGradient>
<linearGradient id="hz" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#ffffff" stop-opacity=".4"/></linearGradient>
<clipPath id="wave"><path d="{shape}"/></clipPath>
<style>
@keyframes pulse{{0%{{opacity:.9;transform:scale(1)}}100%{{opacity:0;transform:scale(2.6)}}}}
.pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2.2s ease-out infinite}}
@keyframes dash{{to{{stroke-dashoffset:-240}}}}
.dash{{animation:dash 14s linear infinite}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
.bob{{animation:bob 2.6s ease-in-out infinite}}
@keyframes blink{{50%{{opacity:.25}}}}
.blink{{animation:blink 1.4s steps(2) infinite}}
@keyframes stripes{{to{{transform:translateX(16px)}}}}
.stripes{{animation:stripes .8s linear infinite}}
</style>
</defs>
<g clip-path="url(#wave)">
<rect width="{W}" height="{h}" fill="url(#bgg)"/>
<rect width="{W}" height="{h}" fill="url(#dots)"/>
{deco}
</g>
{diamond(33, 34 + (8 if i else 0), 10, c['accent'])}
{text(48, 39 + (8 if i else 0), c['title'], 13, C['ink'], 700, MONO, ls=3)}
{text(48 + tw + 12, 39 + (8 if i else 0), c['sub'], 13, C['ink3'], 400, MONO, ls=1)}
<line x1="{line_x:.1f}" y1="{34 + (8 if i else 0)}" x2="{W - 104}" y2="{34 + (8 if i else 0)}" stroke="{C['line']}"/>
<g class="bob">{diamond(W - 84, 34 + (8 if i else 0), 7, C['lime'])}</g>
<g class="bob" style="animation-delay:-.6s">{diamond(W - 66, 34 + (8 if i else 0), 7, '#ffffff')}</g>
<g class="bob" style="animation-delay:-1.2s">{diamond(W - 48, 34 + (8 if i else 0), 7, C['game'])}</g>
<g transform="translate(0 {8 if i else 0})">{c['body']}</g>
</svg>
'''
        with open(os.path.join(ASSETS, c["name"]), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print("wrote", c["name"], f"{len(svg) // 1024} KB")


# ---------- about ----------
def about():
    rows = [
        (C["acc"], "Product developer", "Ships MVPs fast, then turns the ones that work into production systems."),
        (C["game"], "Game developer", "Prototypes mechanics until they're fun: C#, Unity and browser games."),
        (C["lime"], "Software Engineering", "4th year at Sakarya University, Erasmus+ semester at Hochschule Aalen."),
        (C["acc"], "Community", "Organizer of Google Developer Groups on Campus Sakarya."),
        (C["game"], "Open to work", "Freelance and part-time: websites, e-commerce, MVPs, game prototypes."),
    ]
    cx, cy, r = 128, 178, 82
    body = [f'<defs><clipPath id="ph"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>',
            f'<circle cx="{cx}" cy="{cy}" r="{r + 7}" fill="none" stroke="url(#edge)" stroke-width="3"/>',
            f'<circle cx="{cx}" cy="{cy}" r="{r + 7}" fill="none" stroke="{C["lime"]}" stroke-width="2" stroke-dasharray="3 9" class="dash"/>',
            f'<image href="data:image/jpeg;base64,{b64(os.path.join(SRC, "arda-small.jpg"))}" x="{cx - 92}" y="{cy - 112}" width="184" height="230" clip-path="url(#ph)" preserveAspectRatio="xMidYMid slice"/>',
            f'<rect x="{cx - 62}" y="{cy + r - 4}" width="124" height="24" rx="7" fill="#16150f" transform="rotate(-3 {cx} {cy + r + 8})"/>',
            text(cx, cy + r + 13, "PLAYER 1 · ARDA", 10.5, "#ffffff", 700, MONO, "middle", 1.5, f'transform="rotate(-3 {cx} {cy + r + 8})"'),
            text(cx, cy + r + 50, "Sakarya, Türkiye", 12, C["ink3"], 400, MONO, "middle", 1)]
    y = 92
    for col, label, desc in rows:
        body.append(diamond(268, y - 5, 8, col))
        body.append(text(284, y, label, 15.5, C["ink"], 700))
        body.append(text(284, y + 21, desc, 13.5, C["ink2"]))
        y += 52
    card("about.svg", 368, "ABOUT ME", "· PLAYER PROFILE", "\n".join(body),
         aria="About me: product developer, game developer, Software Engineering student at Sakarya University, GDG on Campus organizer, open to freelance work.")


# ---------- right now ----------
def right_now():
    quests = [
        ("Run the 2026–27 season of GDG on Campus Sakarya", "Hackathons, tea talks and workshops", "ACTIVE", C["acc"]),
        ("Polish timucin.site", "Motion design, case studies and a themed CV", "ONGOING", C["game"]),
        ("Freelance builds", "Websites and e-commerce for small businesses", "OPEN", C["lime"]),
        ("Final year of Software Engineering", "Sakarya University", "FINAL YEAR", C["ink2"]),
    ]
    body, y = [], 78
    for title_, desc, tag, col in quests:
        body.append(f'<rect x="28" y="{y}" width="{W - 56}" height="62" rx="12" fill="{C["card"]}" stroke="{C["line"]}"/>')
        body.append(f'<rect x="46" y="{y + 20}" width="20" height="20" rx="4" fill="none" stroke="{col}" stroke-width="2"/>')
        body.append(f'<rect x="51" y="{y + 25}" width="10" height="10" rx="1" fill="{col}" class="blink"/>' if tag in ("ACTIVE", "ONGOING") else
                    f'<rect x="51" y="{y + 25}" width="10" height="10" rx="1" fill="{col}" fill-opacity=".5"/>')
        body.append(text(84, y + 27, title_, 15, C["ink"], 700))
        body.append(text(84, y + 47, desc, 13, C["ink2"]))
        body.append(pill(W - 46, y + 34, tag, col))
        y += 74
    card("now.svg", y + 14, "RIGHT NOW", "· QUEST LOG", "\n".join(body), accent=C["game_d"],
         aria="Right now: running the GDG on Campus Sakarya season, polishing timucin.site, taking freelance builds, final year of Software Engineering.")


# ---------- featured work ----------
def featured():
    items = [
        ("nellkopya.com", "LIVE", C["green"], "Corporate e-commerce for a toner supplier: auth, inventory, cart and admin panel, taken from MVP to production.", "Node.js · Express · React · PostgreSQL · Docker", C["acc"]),
        ("Apoclimate", "PLAYABLE", C["game"], "Climate-themed bunker management game set in 2071: balance energy, water, food, waste and carbon over 5 days.", "Phaser · JavaScript", C["game"]),
        ("timucin.site", "LIVE", C["green"], "Bilingual portfolio with an SVG motion layer, case studies, service pricing and a themed CV.", "HTML · CSS · JS · Railway", C["acc"]),
        ("GeneticAlgorithm", "REPO", C["ink2"], "A genetic algorithm that evolves and tests algorithmic trading strategies on market data.", "Python · Pandas", C["lime"]),
    ]
    cw, ch, gap = (W - 56 - 16) / 2, 168, 16
    body = []
    for i, (name, badge, bcol, desc, stack, scol) in enumerate(items):
        x = 28 + (i % 2) * (cw + gap)
        y = 66 + (i // 2) * (ch + gap)
        body.append(f'<rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="{ch}" rx="14" fill="{C["card"]}" stroke="{C["line"]}"/>')
        body.append(f'<rect x="{x:.1f}" y="{y}" width="4" height="{ch}" rx="2" fill="{scol}"/>')
        body.append(text(x + 22, y + 34, name, 18, C["ink"], 700))
        if badge == "LIVE":
            bx = x + cw - 22 - (len(badge) * 10 * 0.66 + 20) - 14
            body.append(f'<circle cx="{bx:.1f}" cy="{y + 29}" r="4" fill="{C["green"]}" class="pulse"/><circle cx="{bx:.1f}" cy="{y + 29}" r="4" fill="{C["green"]}"/>')
        body.append(pill(x + cw - 20, y + 34, badge, bcol))
        body.append(lines_at(x + 22, y + 62, wrap(desc, cw - 44, 13.5), 13.5, fill=C["ink2"]))
        body.append(text(x + 22, y + ch - 20, stack, 12, scol, 400, MONO))
    card("featured.svg", 66 + 2 * ch + gap + 28, "FEATURED WORK", "· QUESTS CLEARED", "\n".join(body),
         aria="Featured work: nellkopya.com (live e-commerce), Apoclimate (playable game), timucin.site (portfolio), GeneticAlgorithm (trading research).")


# ---------- game showcase ----------
def game():
    ix, iy, iw = 28, 64, W - 56
    ih = iw * 450 / 800
    shot = b64(os.path.join(SRC, "apoclimate.jpg"))
    by = iy + ih
    body = [f'<defs><clipPath id="shot"><rect x="{ix}" y="{iy}" width="{iw}" height="{ih:.1f}" rx="14"/></clipPath>'
            f'<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#0b0a08" stop-opacity="0"/><stop offset="1" stop-color="#0b0a08" stop-opacity=".95"/></linearGradient></defs>',
            f'<image href="data:image/jpeg;base64,{shot}" x="{ix}" y="{iy}" width="{iw}" height="{ih:.1f}" clip-path="url(#shot)" preserveAspectRatio="xMidYMid slice"/>',
            f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih:.1f}" rx="14" fill="url(#fade)"/>',
            f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih:.1f}" rx="14" fill="none" stroke="#ffffff" stroke-opacity=".55" stroke-width="2"/>',
            text(ix + 26, by - 92, "YEŞİLVADİ · 2071", 12, C["lime"], 700, MONO, ls=3),
            text(ix + 24, by - 52, "Apoclimate", 40, "#ffffff", 800),
            text(ix + 26, by - 24, "Keep a climate bunker alive for 5 days. Easy fixes come with a carbon price.", 14, "#e6e2d6"),
            f'<rect x="{ix + iw - 214}" y="{by - 70}" width="190" height="44" rx="22" fill="#ffffff"/>',
            text(ix + iw - 119, by - 42.5, "▶  PLAY IN BROWSER", 13, C["game_d"], 700, MONO, "middle", 1.5)]
    y2 = by + 34
    feats = [("ENERGY · WATER · FOOD", C["acc"]), ("WASTE · CARBON", C["lime"]), ("RESIDENTS & TRUST", C["game"]), ("WHO GETS IN?", C["ink2"])]
    x = 28
    for label, col in feats:
        w_ = len(label) * 10 * 0.66 + 26
        body.append(f'<rect x="{x}" y="{y2 - 15}" width="{w_:.1f}" height="24" rx="12" fill="{col}" fill-opacity=".1" stroke="{col}" stroke-opacity=".5"/>')
        body.append(text(x + w_ / 2, y2 + 1.5, label, 10, col, 700, MONO, "middle", 1.2))
        x += w_ + 10
    card("game.svg", int(y2 + 30), "GAME SHOWCASE", "· NOW PLAYING", "\n".join(body), accent=C["game_d"],
         aria="Game showcase: Apoclimate, a climate-themed bunker management game set in Yeşilvadi, 2071. Play in browser.")


# ---------- services ----------
def services():
    rows = [
        ("WEB", "Business website", "Custom design, SEO basics, WhatsApp, maps and contact form", "1–2 weeks", "₺15,000", C["acc"]),
        ("SHOP", "E-commerce", "Products, stock, cart, orders, payments and an admin panel", "3–5 weeks", "₺40,000", C["acc"]),
        ("MVP", "MVP / web app", "Core feature first, built to scale if it works", "2–6 weeks", "₺30,000", C["lime"]),
        ("GAME", "Game prototype", "A playable core mechanic with a new build every week", "2–4 weeks", "₺20,000", C["game"]),
        ("CARE", "Care & hosting", "Hosting, domain, SSL, backups and small edits", "monthly", "₺1,500/mo", C["ink2"]),
    ]
    body, y = [], 74
    for tag, name, desc, dur, price, col in rows:
        body.append(f'<rect x="28" y="{y}" width="{W - 56}" height="58" rx="12" fill="{C["card"]}" stroke="{C["line"]}"/>')
        body.append(f'<rect x="42" y="{y + 11}" width="52" height="36" rx="9" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".6"/>')
        body.append(text(68, y + 33.5, tag, 11, col, 700, MONO, "middle", 1.5))
        body.append(text(110, y + 25, name, 15.5, C["ink"], 700))
        body.append(text(110, y + 45, desc, 12.5, C["ink2"]))
        body.append(text(W - 268, y + 25, "FROM", 10, C["ink3"], 700, MONO, ls=2))
        body.append(text(W - 268, y + 45, dur, 11.5, C["ink3"], 400, MONO))
        body.append(text(W - 46, y + 39, price, 24, col, 400, SERIF, "end", extra='font-style="italic"'))
        y += 68
    y += 14
    body.append(f'<rect x="28" y="{y}" width="178" height="44" rx="22" fill="#ffffff"/>')
    body.append(text(117, y + 27.5, "GET A QUOTE  →", 13, "#d9481a", 700, MONO, "middle", 1.5))
    body.append(text(224, y + 27, "Fixed quote after a free 30-minute call · timucin.site", 13, C["ink2"]))
    card("services.svg", y + 72, "SERVICES", "· ITEM SHOP", "\n".join(body),
         aria="Services: business website from ₺15,000, e-commerce from ₺40,000, MVP from ₺30,000, game prototype from ₺20,000, care and hosting from ₺1,500 a month.")


# ---------- tech stack ----------
def stack():
    groups = [
        ("WEB", C["acc"], ["js", "ts", "nodejs", "express", "react", "html", "css"]),
        ("DATA & OPS", C["lime"], ["postgres", "mongodb", "docker", "linux", "git", "github"]),
        ("LANGUAGES", C["game"], ["cs", "dotnet", "java", "spring", "py"]),
        ("GAMES", C["game"], ["unity", "unreal"]),
    ]
    body, y, size, gap = [], 74, 48, 12
    for gi, (label, col, ids) in enumerate(groups):
        body.append(text(28, y + 30, label, 11, col, 700, MONO, ls=2))
        x = 170
        for ic in ids:
            req = urllib.request.Request(f"https://skillicons.dev/icons?i={ic}", headers={"User-Agent": "profile-readme-bot"})
            svg = urllib.request.urlopen(req, timeout=30).read().decode()
            inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
            vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
            p = f"i{gi}{ic}_"
            inner = re.sub(r'id="([^"]+)"', lambda m: f'id="{p}{m.group(1)}"', inner)
            inner = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{p}{m.group(1)})", inner)
            inner = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{p}{m.group(1)}"', inner)
            body.append(f'<svg x="{x}" y="{y + 2}" width="{size}" height="{size}" viewBox="{vb}">{inner}</svg>')
            x += size + gap
        y += size + 22
        if gi < len(groups) - 1:
            body.append(f'<line x1="28" y1="{y - 10}" x2="{W - 28}" y2="{y - 10}" stroke="{C["line"]}" stroke-dasharray="2 6"/>')
    card("stack.svg", y + 16, "TECH STACK", "· SKILL TREE", "\n".join(body), accent=C["lime"],
         aria="Tech stack: JavaScript, TypeScript, Node.js, Express, React, HTML, CSS, PostgreSQL, MongoDB, Docker, Linux, Git, GitHub, C#, .NET, Java, Spring, Python, Unity, Unreal Engine.")


# ---------- events (dynamic) ----------
def events():
    url = f"https://gdg.community.dev/api/event/?chapter={GDG_CHAPTER}&page_size=20&order=-start_date"
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "profile-readme-bot"}), timeout=30))
    evs = [e for e in data["results"] if e.get("status") == "Published" and not e.get("is_hidden") and not e.get("is_test")]
    evs.sort(key=lambda e: e["start_date"], reverse=True)
    evs = evs[:5]
    now = datetime.datetime.now(datetime.timezone.utc)
    body, y = [], 76
    if evs:
        body.append(f'<line x1="46" y1="{y + 8}" x2="46" y2="{y + 8 + (len(evs) - 1) * 62}" stroke="url(#hz)" stroke-width="2"/>')
    for ev in evs:
        start = datetime.datetime.fromisoformat(ev["start_date"])
        upcoming = start > now
        title_ = re.sub(r"^GDG on Campus Sakarya (University|Üniversitesi) - ", "", ev["title"])
        col = C["lime"] if upcoming else C["acc"]
        if upcoming:
            body.append(f'<circle cx="46" cy="{y + 8}" r="7" fill="{col}" class="pulse"/>')
        body.append(diamond(46, y + 8, 11, col if upcoming else C["bg"], f'stroke="{col}" stroke-width="2"'))
        body.append(text(72, y + 4, start.strftime("%d %b %Y").upper(), 11, C["ink3"], 700, MONO, ls=1.5))
        body.append(text(72, y + 26, title_, 16, C["ink"], 700))
        body.append(pill(W - 46, y + 20, "UPCOMING" if upcoming else "DONE", col))
        y += 62
    if not evs:
        body.append(text(46, y + 20, "No events yet. Follow the chapter page to hear about the next one.", 14, C["ink2"]))
        y += 50
    body.append(text(28, y + 18, f"Auto-updated daily from gdg.community.dev · last run {now:%d %b %Y}", 11.5, C["ink3"], 400, MONO))
    card("events.svg", y + 46, "GDG ON CAMPUS SAKARYA", "· EVENTS", "\n".join(body), accent=C["lime"],
         aria="Latest GDG on Campus Sakarya events: " + "; ".join(f'{e["title"]} ({e["start_date"][:10]})' for e in evs))


# ---------- stats (dynamic) ----------
def gh_token():
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    return tok


def stats():
    q = """query($login:String!){user(login:$login){
      followers{totalCount}
      contributionsCollection{contributionCalendar{totalContributions}}
      repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount
        nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q, "variables": {"login": USER}}).encode(),
                                 headers={"Authorization": f"bearer {gh_token()}", "User-Agent": "profile-readme-bot", "Content-Type": "application/json"})
    u = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            langs.setdefault(n, [0, e["node"]["color"] or "#888"])
            langs[n][0] += e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(v[0] for _, v in top) or 1
    tiles = [("CONTRIBUTIONS", u["contributionsCollection"]["contributionCalendar"]["totalContributions"], "last 12 months", C["acc"]),
             ("PUBLIC REPOS", u["repositories"]["totalCount"], "owned, no forks", C["game"]),
             ("STARS EARNED", stars, "across public repos", C["lime"]),
             ("FOLLOWERS", u["followers"]["totalCount"], "on GitHub", C["ink2"])]
    body, tw_, gap = [], (W - 56 - 3 * 12) / 4, 12
    for i, (label, num, sub, col) in enumerate(tiles):
        x = 28 + i * (tw_ + gap)
        body.append(f'<rect x="{x:.1f}" y="70" width="{tw_:.1f}" height="102" rx="12" fill="{C["card"]}" stroke="{C["line"]}"/>')
        body.append(f'<rect x="{x + 18:.1f}" y="70" width="34" height="3" rx="1.5" fill="{col}"/>')
        body.append(text(x + 18, 98, label, 10.5, C["ink3"], 700, MONO, ls=1.5))
        body.append(text(x + 18, 140, f"{num:,}", 36, C["ink"], 800))
        body.append(text(x + 18, 160, sub, 11.5, col, 400, MONO))
    y = 210
    body.append(text(28, y, "TOP LANGUAGES", 10.5, C["ink3"], 700, MONO, ls=1.5))
    body.append(text(W - 28, y, "by code size in public repos", 11, C["ink3"], 400, MONO, "end"))
    bx, by_, bw = 28, y + 14, W - 56
    body.append(f'<defs><clipPath id="bar"><rect x="{bx}" y="{by_}" width="{bw}" height="14" rx="7"/></clipPath></defs><g clip-path="url(#bar)">')
    x = bx
    for name, (size, col) in top:
        w_ = bw * size / total
        body.append(f'<rect x="{x:.1f}" y="{by_}" width="{w_ + .5:.1f}" height="14" fill="{col}"/>')
        x += w_
    body.append("</g>")
    x, ly = 28, by_ + 44
    for name, (size, col) in top:
        label = f"{name} {size / total * 100:.0f}%"
        body.append(f'<circle cx="{x + 5}" cy="{ly - 4}" r="5" fill="{col}"/>')
        body.append(text(x + 16, ly, label, 13, C["ink2"]))
        x += width(label, 13, 0.56) + 40
    card("stats.svg", ly + 30, "GITHUB STATS", "· XP", "\n".join(body),
         aria=f"GitHub stats: {tiles[0][1]} contributions in the last year, {tiles[1][1]} public repos, {stars} stars, {tiles[3][1]} followers. Top languages: " + ", ".join(n for n, _ in top))


if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    for fn in (about, right_now, featured, game, services, stack, events, stats):
        fn()
    render_all()
