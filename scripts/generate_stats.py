"""Gera assets/stats.svg e assets/langs.svg com os dados reais do GitHub.
Uso: GITHUB_TOKEN=... python scripts/generate_stats.py [usuario]
Sem token (ou com --placeholder) gera cards vazios de espera."""
import json, math, os, sys, urllib.request

LOGIN = next((a for a in sys.argv[1:] if not a.startswith("--")), "MarcosUkyo")
TOKEN = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
BG, BORDER, TITLE, TEXT, MUTED = "#1a1b27", "#2f3149", "#3DDC84", "#c0caf5", "#7a82a8"
ACCENT = "#A78BFA"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
PALETTE = ["#A78BFA", "#3DDC84", "#7AA2F7", "#F7768E", "#E0AF68", "#73DACA", "#BB9AF7"]

QUERY = """query($login:String!){user(login:$login){
 followers{totalCount}
 pullRequests{totalCount}
 issues{totalCount}
 repositories(ownerAffiliations:[OWNER],isFork:false,first:100,privacy:PUBLIC){totalCount nodes{stargazerCount
  languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}
 contributionsCollection{totalCommitContributions totalPullRequestReviewContributions
  contributionCalendar{totalContributions}}}}"""

def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in d: raise SystemExit(d["errors"])
    u = d["data"]["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            l = langs.setdefault(n, {"size": 0, "repos": 0, "color": e["node"]["color"]})
            l["size"] += e["size"]; l["repos"] += 1
    cc = u["contributionsCollection"]
    return {"commits": cc["totalCommitContributions"], "contrib": cc["contributionCalendar"]["totalContributions"],
            "reviews": cc["totalPullRequestReviewContributions"], "prs": u["pullRequests"]["totalCount"],
            "issues": u["issues"]["totalCount"], "repos": u["repositories"]["totalCount"],
            "stars": sum(r["stargazerCount"] for r in repos), "followers": u["followers"]["totalCount"],
            "langs": langs}

def card(w, h, title, inner):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>text{{font-family:{FONT}}} .t{{fill:{TITLE};font-size:18px;font-weight:700}} .l{{fill:{TEXT};font-size:14px}}
.v{{fill:{ACCENT};font-size:15px;font-weight:700}} .m{{fill:{MUTED};font-size:11px}}
@keyframes in{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}} .r{{animation:in .6s ease both}}</style>
<rect x=".5" y=".5" rx="12" width="{w-1}" height="{h-1}" fill="{BG}" stroke="{BORDER}"/>
<text x="24" y="34" class="t">{title}</text>{inner}</svg>'''

def stats_svg(d):
    f = lambda k: "—" if d is None else f"{d[k]:,}".replace(",", ".")
    rows = [("", "Commits no ano", "commits"), ("", "Pull requests", "prs"), ("", "Issues", "issues"),
            ("", "Repositórios", "repos"), ("", "Estrelas", "stars"), ("", "Seguidores", "followers")]
    inner = ""
    for i, (ic, lb, k) in enumerate(rows):
        x, y = 24 + (i % 2) * 245, 74 + (i // 2) * 38
        inner += f'<g class="r" style="animation-delay:{i*.08}s"><text x="{x}" y="{y}" class="l">{lb}</text><text x="{x+195}" y="{y}" class="v" text-anchor="end">{f(k)}</text></g>'
    total = "—" if d is None else f"{d['contrib']:,}".replace(",", ".")
    inner += f'<line x1="24" x2="471" y1="170" y2="170" stroke="{BORDER}"/><text x="24" y="196" class="m">Contribuições no último ano</text><text x="471" y="198" class="v" text-anchor="end" style="font-size:18px">{total}</text>'
    if d is None: inner += f'<text x="471" y="34" class="m" text-anchor="end">atualizando…</text>'
    return card(495, 215, "Estatísticas do GitHub", inner)

def langs_svg(d):
    inner = ""
    langs = [] if d is None else sorted(d["langs"].items(), key=lambda x: -x[1]["size"])[:6]
    total = sum(l["size"] for _, l in langs) or 1
    cx, cy, r = 105, 128, 55; circ = 2 * math.pi * r
    inner += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="22"/>'
    off = 0
    for i, (n, l) in enumerate(langs):
        c = l["color"] or PALETTE[i % len(PALETTE)]; c = PALETTE[i % len(PALETTE)] if i < len(PALETTE) else c
        ln = circ * l["size"] / total
        inner += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="22" stroke-dasharray="{max(ln-2,0.1):.2f} {circ:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        off += ln
        y = 66 + i * 28
        pct = l["size"] * 100 / total
        inner += f'<g class="r" style="animation-delay:{i*.08}s"><circle cx="228" cy="{y-5}" r="5" fill="{c}"/><text x="242" y="{y}" class="l">{n}</text><text x="385" y="{y}" class="m" text-anchor="end">{l["repos"]} repo{"s" if l["repos"]!=1 else ""}</text><text x="470" y="{y}" class="v" text-anchor="end">{pct:.1f}%</text></g>'
    if not langs: inner += f'<text x="{cx}" y="{cy+4}" class="m" text-anchor="middle">atualizando…</text>'
    return card(495, 250, "Linguagens Mais Usadas", inner)

def main():
    placeholder = "--placeholder" in sys.argv or not TOKEN
    d = None if placeholder else fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("stats.svg", stats_svg), ("langs.svg", langs_svg)):
        p = os.path.join(OUT, name)
        if placeholder and os.path.exists(p): continue
        open(p, "w", encoding="utf-8").write(fn(d))
    print("ok", "placeholder" if placeholder else "dados reais")

if __name__ == "__main__": main()
