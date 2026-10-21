#!/usr/bin/env python3
"""HR 知識庫靜態網站建置器。

擴充方式：
  1. 在 data/decks/ 新增一個簡報 JSON（格式見 docs/SCHEMA.md）
  2. 在 data/catalog.json 的 decks 加一筆 {id, file, slug, domain}
  3. 執行 python build.py  → 重新產生 index.html、decks/*.html、search-index.json
"""
import html, json, sys
from pathlib import Path

ROOT = Path(__file__).parent
E = html.escape


def esc(s):
    return E(str(s or ""))


# ---------- slide renderers ----------
def notes_html(s):
    n = s.get("notes") or []
    return '<div class="notes">' + "".join(f"<p>{esc(x)}</p>" for x in n) + "</div>" if n else ""


def head(s, label):
    return (f'<div class="kicker">{esc(label)}</div>'
            f'<h2 class="conclusion">{esc(s.get("title"))}</h2>')


def r_cover(s, deck):
    return (f'<div class="cover"><div class="kicker light">人力資源管理知識庫 · 書籍導讀</div>'
            f'<h1>{esc(deck["title"])}</h1>'
            f'<div class="sub">{esc(deck.get("subtitle"))}</div>'
            f'<div class="author">{esc(deck["author"])}</div>'
            f'<div class="claim"><span>核心主張</span>{esc(deck.get("claim"))}</div></div>')


def r_arch(s, deck):
    layers = (s.get("layers") or [])[:3]
    cols = []
    for i, l in enumerate(layers):
        chs = "".join(f"<li>{esc(c)}</li>" for c in l.get("chapters", []))
        arrow = '<div class="arrow">→</div>' if i < len(layers) - 1 else ""
        cols.append(f'<div class="layer"><div class="num">{i+1}</div><h3>{esc(l.get("label"))}</h3>'
                    f'<p>{esc(l.get("desc"))}</p><ul>{chs}</ul></div>{arrow}')
    rel = f'<div class="relation"><b>互相支撐：</b>{esc(s.get("relation"))}</div>' if s.get("relation") else ""
    return head(s, "全書架構圖") + f'<div class="arch">{"".join(cols)}</div>{rel}'


def r_chapter(s, deck):
    hl = (s.get("highlights") or [])[:3]
    cards = []
    for h in hl:
        stat = f'<div class="stat">{esc(h.get("stat"))}</div>' if h.get("stat") else ""
        cards.append(f'<div class="card">{stat}<h4>{esc(h.get("head"))}</h4><p>{esc(h.get("body"))}</p></div>')
    return (head(s, "逐章重點 · " + str(s.get("chapters", ""))) +
            f'<div class="problem"><span>核心論點</span>{esc(s.get("problem"))}</div>'
            f'<div class="cards n{len(cards)}">{"".join(cards)}</div>'
            f'<div class="oneliner">{esc(s.get("oneliner"))}</div>')


def r_flow(s, deck):
    steps = s.get("steps") or []
    out = []
    for i, st in enumerate(steps):
        nxt = f'<div class="leads">↳ {esc(st.get("leads_to"))}</div>' if st.get("leads_to") else ""
        out.append(f'<div class="step"><div class="chev"><b>{i+1}</b>{esc(st.get("chapter"))}</div>'
                   f'<div class="concl">{esc(st.get("conclusion"))}</div>{nxt}</div>')
    return head(s, "章節脈絡") + f'<div class="flow n{len(steps)}">{"".join(out)}</div>'


def r_summary(s, deck):
    pts = "".join(f'<li><b>{i+1}</b><span>{esc(p)}</span></li>' for i, p in enumerate(s.get("points", [])))
    return (head(s, "總結") + f'<ol class="points">{pts}</ol>'
            f'<div class="action"><span>立刻可應用的一件事</span>{esc(s.get("action"))}</div>')


def r_appendix(s, deck):
    rows = "".join(f'<tr><td>{esc(i.get("ref"))}</td><td>{esc(i.get("why"))}</td></tr>' for i in s.get("items", []))
    return head(s, "附錄 · 延伸閱讀") + f'<table class="appx"><thead><tr><th>位置</th><th>為何值得深挖</th></tr></thead><tbody>{rows}</tbody></table>'


RENDER = {"cover": r_cover, "architecture": r_arch, "chapter": r_chapter,
          "flow": r_flow, "summary": r_summary, "appendix": r_appendix}


def slide_text(s):
    """攤平成可搜尋文字"""
    parts = [s.get("title", ""), s.get("chapters", ""), s.get("problem", ""), s.get("oneliner", ""),
             s.get("relation", ""), s.get("action", "")]
    for l in s.get("layers", []):
        parts += [l.get("label", ""), l.get("desc", "")] + l.get("chapters", [])
    for h in s.get("highlights", []):
        parts += [h.get("head", ""), h.get("body", ""), h.get("stat", "")]
    for st in s.get("steps", []):
        parts += [st.get("chapter", ""), st.get("conclusion", ""), st.get("leads_to", "")]
    parts += s.get("points", [])
    for i in s.get("items", []):
        parts += [i.get("ref", ""), i.get("why", "")]
    parts += s.get("keywords", [])
    parts += s.get("notes", [])
    return " ".join(p for p in parts if p)


TYPE_LABEL = {"cover": "封面", "architecture": "架構圖", "chapter": "逐章重點",
              "flow": "章節脈絡", "summary": "總結", "appendix": "附錄"}


def build_deck(deck, cat, domains):
    slides = deck["slides"]
    total = len(slides)
    secs, thumbs = [], []
    for i, s in enumerate(slides):
        body = RENDER.get(s["type"], r_chapter)(s, deck)
        secs.append(f'<section class="slide t-{s["type"]}" id="s{i+1}" data-i="{i}"><div class="inner">{body}</div>'
                    f'<div class="foot"><span>{esc(deck["title"])}</span><span>{i+1} / {total}</span></div>{notes_html(s)}</section>')
        t = s.get("chapters") or TYPE_LABEL.get(s["type"], "")
        thumbs.append(f'<a href="#s{i+1}" data-go="{i}"><b>{i+1}</b> {esc(t)}<small>{esc(s.get("title"))}</small></a>')
    dom = domains.get(cat["domain"], {}).get("name", "")
    page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(deck["title"])}｜HR 知識庫</title>
<link rel="stylesheet" href="../assets/style.css"></head>
<body class="deckpage">
<header class="bar"><a href="../index.html" class="home">← 知識地圖</a>
<span class="crumb">{esc(dom)} / {esc(deck["title"])}</span>
<span class="tools"><button id="btnNotes" title="講稿 (N)">講稿</button><button id="btnList" title="目錄 (G)">目錄</button><button id="btnFs" title="全螢幕 (F)">全螢幕</button><button onclick="window.print()" title="列印/PDF">PDF</button></span></header>
<nav id="toc" class="toc hidden">{"".join(thumbs)}</nav>
<main id="viewport"><div id="stage">{"".join(secs)}</div></main>
<div class="ctrl"><button id="prev">‹</button><div class="prog"><i id="progbar"></i></div><button id="next">›</button></div>
<script src="../assets/deck.js"></script></body></html>'''
    (ROOT / "decks" / f'{cat["slug"]}.html').write_text(page, encoding="utf-8")


def main():
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    domains = {d["id"]: d for d in catalog["domains"]}
    (ROOT / "decks").mkdir(exist_ok=True)
    index, cards_by_domain = [], {d["id"]: [] for d in catalog["domains"]}
    for cat in catalog["decks"]:
        deck = json.loads((ROOT / "data" / "decks" / cat["file"]).read_text(encoding="utf-8"))
        build_deck(deck, cat, domains)
        url = f'decks/{cat["slug"]}.html'
        kws = deck.get("keywords", [])
        index.append({"deck": deck["title"], "author": deck["author"], "domain": domains[cat["domain"]]["name"],
                      "url": url, "n": 1, "type": "書籍總覽", "title": deck.get("claim", ""),
                      "text": " ".join([deck["title"], deck.get("subtitle", ""), deck["author"], deck.get("claim", ""),
                                        deck.get("audience", "")] + kws)})
        for i, s in enumerate(deck["slides"]):
            index.append({"deck": deck["title"], "author": deck["author"], "domain": domains[cat["domain"]]["name"],
                          "url": url, "n": i + 1, "type": s.get("chapters") or TYPE_LABEL.get(s["type"], ""),
                          "title": s.get("title", ""), "text": slide_text(s)})
        cards_by_domain[cat["domain"]].append(
            f'<a class="deck" href="{url}"><div class="cat">{esc(deck.get("category"))}</div>'
            f'<h4>《{esc(deck["title"])}》</h4><div class="au">{esc(deck["author"])}</div>'
            f'<p>{esc(deck.get("claim"))}</p><div class="meta">{len(deck["slides"])} 頁簡報 · {esc(deck.get("audience",""))}</div></a>')
    (ROOT / "search-index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    sections = []
    for d in catalog["domains"]:
        cs = cards_by_domain[d["id"]]
        body = "".join(cs) if cs else '<div class="soon">規劃中 · 資料擴充後將於此出現</div>'
        sections.append(f'<section class="domain" data-domain="{esc(d["name"])}"><div class="dhead"><h3>{esc(d["name"])}</h3>'
                        f'<p>{esc(d["desc"])}</p><span class="count">{len(cs)} 份</span></div><div class="decks">{body}</div></section>')
    nd, ns = len(catalog["decks"]), len(index)
    home = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>人力資源管理知識庫</title><link rel="stylesheet" href="assets/style.css"></head>
<body class="homepage">
<header class="hero"><div class="wrap"><div class="kicker light">HR KNOWLEDGE BASE</div>
<h1>人力資源管理知識庫</h1>
<p>{esc(catalog.get("tagline"))}</p>
<div class="searchbox"><input id="q" type="search" placeholder="輸入關鍵字，例如：薪酬、績效、OKR、人才盤點…" autofocus autocomplete="off">
<div class="chips" id="chips"></div></div>
<div class="stats"><div><b>{nd}</b>本書籍簡報</div><div><b>{ns}</b>筆可搜尋內容</div><div><b>{len(catalog["domains"])}</b>個知識領域</div></div></div></header>
<main class="wrap"><div id="results" class="results hidden"></div>
<div id="map"><h2 class="maptitle">知識地圖 <small>點選書籍進入導讀簡報</small></h2>{"".join(sections)}</div></main>
<footer class="wrap foot2">內容依各書原文整理；書中未載之處標註「原文未載」。更新：{esc(catalog.get("updated"))}</footer>
<script src="assets/search.js"></script></body></html>'''
    (ROOT / "index.html").write_text(home, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("")
    print(f"built {nd} decks, {ns} index entries")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
