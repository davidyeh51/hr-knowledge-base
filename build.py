#!/usr/bin/env python3
"""HR 知識庫靜態網站建置器。

擴充方式：
  1. 在 data/decks/ 新增一個簡報 JSON（格式見 docs/SCHEMA.md，可選內嵌 svg 與 image）
  2. 在 data/catalog.json 的 decks 加一筆 {id, file, slug, domain, notion, notionSub}
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
    img = s.get("image")
    left = (f'<div class="cover-main"><div class="kicker light">人力資源管理知識庫 · 10 分鐘麥肯錫風格導讀</div>'
            f'<h1>{esc(deck["title"])}</h1>'
            f'<div class="sub">{esc(deck.get("subtitle"))}</div>'
            f'<div class="author">{esc(deck["author"])}</div>'
            f'<div class="claim"><span>核心主張</span>{esc(deck.get("claim"))}</div></div>')
    if img:
        right = (f'<div class="cover-art"><div class="book-frame">'
                 f'<img src="{esc(img)}" alt="{esc(deck["title"])} 主題視覺重繪">'
                 f'<div class="book-cap"><span>REDRAWN VISUAL</span>{esc(deck["title"])}</div>'
                 f'</div></div>')
        return f'<div class="cover with-img">{left}{right}</div>'
    return f'<div class="cover">{left}</div>'


def r_arch(s, deck):
    svg = s.get("svg")
    rel = f'<div class="relation"><b>互相支撐：</b>{esc(s.get("relation"))}</div>' if s.get("relation") else ""
    if svg:
        return head(s, "全書架構圖") + f'<div class="svg-stage arch-svg">{svg}</div>{rel}'
    layers = (s.get("layers") or [])[:3]
    cols = []
    for i, l in enumerate(layers):
        chs = "".join(f"<li>{esc(c)}</li>" for c in l.get("chapters", []))
        arrow = '<div class="arrow">→</div>' if i < len(layers) - 1 else ""
        cols.append(f'<div class="layer"><div class="num">{i+1}</div><h3>{esc(l.get("label"))}</h3>'
                    f'<p>{esc(l.get("desc"))}</p><ul>{chs}</ul></div>{arrow}')
    return head(s, "全書架構圖") + f'<div class="arch">{"".join(cols)}</div>{rel}'


def r_chapter(s, deck):
    hl = (s.get("highlights") or [])[:3]
    svg = s.get("svg")
    layout = s.get("layout", "split" if svg else "classic")
    label = "逐章重點 · " + str(s.get("chapters", ""))
    oneliner = f'<div class="oneliner">{esc(s.get("oneliner"))}</div>'

    if svg and layout == "split":
        vcards = []
        for h in hl:
            stat = f'<span class="vstat">{esc(h.get("stat"))}</span>' if h.get("stat") else ""
            vcards.append(f'<div class="vcard"><div class="vhead"><h4>{esc(h.get("head"))}</h4>{stat}</div>'
                          f'<p>{esc(h.get("body"))}</p></div>')
        prob = f'<div class="problem compact"><span>核心論點</span>{esc(s.get("problem"))}</div>'
        return (head(s, label) +
                f'<div class="split-body"><div class="svg-pane">{svg}</div>'
                f'<div class="info-pane">{prob}<div class="vcards">{"".join(vcards)}</div></div></div>'
                + oneliner)

    if svg and layout == "top-svg":
        cards = []
        for h in hl:
            stat = f'<span class="vstat">{esc(h.get("stat"))}</span>' if h.get("stat") else ""
            cards.append(f'<div class="card compact"><div class="vhead"><h4>{esc(h.get("head"))}</h4>{stat}</div>'
                         f'<p>{esc(h.get("body"))}</p></div>')
        return (head(s, label) +
                f'<div class="svg-stage top-svg">{svg}</div>'
                f'<div class="cards compact n{len(cards)}">{"".join(cards)}</div>'
                + oneliner)

    cards = []
    for h in hl:
        stat = f'<div class="stat">{esc(h.get("stat"))}</div>' if h.get("stat") else ""
        cards.append(f'<div class="card">{stat}<h4>{esc(h.get("head"))}</h4><p>{esc(h.get("body"))}</p></div>')
    return (head(s, label) +
            f'<div class="problem"><span>核心論點</span>{esc(s.get("problem"))}</div>'
            f'<div class="cards n{len(cards)}">{"".join(cards)}</div>'
            + oneliner)


def r_flow(s, deck):
    steps = s.get("steps") or []
    out = []
    for i, st in enumerate(steps):
        nxt = f'<div class="leads">↳ {esc(st.get("leads_to"))}</div>' if st.get("leads_to") else ""
        out.append(f'<div class="step"><div class="chev"><b>{i+1}</b>{esc(st.get("chapter"))}</div>'
                   f'<div class="concl">{esc(st.get("conclusion"))}</div>{nxt}</div>')
    return head(s, "章節脈絡") + f'<div class="flow n{len(steps)}">{"".join(out)}</div>'


def r_summary(s, deck):
    img = s.get("image")
    quote = s.get("quote")
    pts = "".join(f'<li><b>{i+1}</b><span>{esc(p)}</span></li>' for i, p in enumerate(s.get("points", [])))
    act = f'<div class="action"><span>立刻可應用的一件事</span>{esc(s.get("action"))}</div>'
    if img:
        qhtml = f'<blockquote class="sum-quote">「{esc(quote)}」</blockquote>' if quote else ""
        return (head(s, "總結與落地行動") +
                f'<div class="sum-grid"><ol class="points compact">{pts}</ol>'
                f'<div class="sum-side"><div class="sum-art"><img src="{esc(img)}" alt="高潛人才斜率複利視覺配圖"></div>{qhtml}</div></div>'
                + act)
    return head(s, "總結") + f'<ol class="points">{pts}</ol>' + act


def r_appendix(s, deck):
    rows = "".join(f'<tr><td>{esc(i.get("ref"))}</td><td>{esc(i.get("why"))}</td></tr>' for i in s.get("items", []))
    return head(s, "附錄 · 延伸閱讀與實證索引") + f'<table class="appx"><thead><tr><th>位置 / 研究</th><th>為何值得深挖</th></tr></thead><tbody>{rows}</tbody></table>'


RENDER = {"cover": r_cover, "architecture": r_arch, "chapter": r_chapter,
          "flow": r_flow, "summary": r_summary, "appendix": r_appendix}


def slide_text(s):
    """攤平成可搜尋文字"""
    parts = [s.get("title", ""), s.get("chapters", ""), s.get("problem", ""), s.get("oneliner", ""),
             s.get("relation", ""), s.get("action", ""), s.get("quote", "")]
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


def build_deck(deck, cat, domains, notion_map):
    slides = deck["slides"]
    total = len(slides)
    secs, thumbs = [], []
    for i, s in enumerate(slides):
        body = RENDER.get(s["type"], r_chapter)(s, deck)
        has_rich = " has-rich" if (s.get("svg") or s.get("image")) else ""
        secs.append(f'<section class="slide t-{s["type"]}{has_rich}" id="s{i+1}" data-i="{i}"><div class="inner">{body}</div>'
                    f'<div class="foot"><span>{esc(deck["title"])}</span><span>{i+1} / {total}</span></div>{notes_html(s)}</section>')
        t = s.get("chapters") or TYPE_LABEL.get(s["type"], "")
        thumbs.append(f'<a href="#s{i+1}" data-go="{i}"><b>{i+1}</b> {esc(t)}<small>{esc(s.get("title"))}</small></a>')
    dom = domains.get(cat["domain"], {}).get("name", "")
    n_sub = cat.get("notionSub") or notion_map.get(cat.get("notion", ""), {}).get("name", "")
    crumb = f"{n_sub} · {dom} / {deck['title']}" if n_sub else f"{dom} / {deck['title']}"
    page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(deck["title"])}｜HR 知識庫</title>
<link rel="stylesheet" href="../assets/style.css"></head>
<body class="deckpage">
<header class="bar"><a href="../index.html" class="home">← 知識地圖</a>
<span class="crumb">{esc(crumb)}</span>
<span class="tools"><button id="btnNotes" title="講稿 (N)">講稿</button><button id="btnList" title="目錄 (G)">目錄</button><button id="btnFs" title="全螢幕 (F)">全螢幕</button><button onclick="window.print()" title="列印/PDF">PDF</button></span></header>
<nav id="toc" class="toc hidden">{"".join(thumbs)}</nav>
<main id="viewport"><div id="stage">{"".join(secs)}</div></main>
<div class="ctrl"><button id="prev">‹</button><div class="prog"><i id="progbar"></i></div><button id="next">›</button></div>
<script src="../assets/deck.js"></script></body></html>'''
    (ROOT / "decks" / f'{cat["slug"]}.html').write_text(page, encoding="utf-8")


def deck_card_html(deck, cat, url, show_notion_tag=True):
    badge = f'<span class="badge">{esc(cat["badge"])}</span>' if cat.get("badge") else ""
    ntag = f'<span class="ntag">{esc(cat.get("notionSub") or cat.get("notion",""))}</span>' if (show_notion_tag and cat.get("notion")) else ""
    return (f'<a class="deck{" featured" if cat.get("badge") else ""}" href="{url}">'
            f'<div class="dtags"><span class="cat">{esc(deck.get("category"))}</span>{ntag}{badge}</div>'
            f'<h4>《{esc(deck["title"])}》</h4><div class="au">{esc(deck["author"])}</div>'
            f'<p>{esc(deck.get("claim"))}</p>'
            f'<div class="meta">{len(deck["slides"])} 頁簡報 · {esc(deck.get("audience",""))}</div></a>')


def main():
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    domains = {d["id"]: d for d in catalog["domains"]}
    notion_list = catalog.get("notionDomains", [])
    notion_map = {n["id"]: n for n in notion_list}
    (ROOT / "decks").mkdir(exist_ok=True)

    index = []
    cards_by_domain = {d["id"]: [] for d in catalog["domains"]}
    cards_by_notion = {n["id"]: [] for n in notion_list}
    active_notion_subs = set()

    for cat in catalog["decks"]:
        deck = json.loads((ROOT / "data" / "decks" / cat["file"]).read_text(encoding="utf-8"))
        build_deck(deck, cat, domains, notion_map)
        url = f'decks/{cat["slug"]}.html'
        dom_name = domains[cat["domain"]]["name"]
        notion_id = cat.get("notion", "")
        notion_name = notion_map.get(notion_id, {}).get("name", "")
        notion_sub = cat.get("notionSub", "")
        if notion_sub:
            active_notion_subs.add(notion_sub)

        kws = deck.get("keywords", [])
        index.append({
            "deck": deck["title"], "author": deck["author"],
            "domain": dom_name, "notion": notion_name, "notionSub": notion_sub,
            "url": url, "n": 1, "type": "書籍總覽", "title": deck.get("claim", ""),
            "text": " ".join([deck["title"], deck.get("subtitle", ""), deck["author"], deck.get("claim", ""),
                              deck.get("audience", ""), notion_name, notion_sub] + kws)
        })
        for i, s in enumerate(deck["slides"]):
            index.append({
                "deck": deck["title"], "author": deck["author"],
                "domain": dom_name, "notion": notion_name, "notionSub": notion_sub,
                "url": url, "n": i + 1, "type": s.get("chapters") or TYPE_LABEL.get(s["type"], ""),
                "title": s.get("title", ""), "text": slide_text(s)
            })

        cards_by_domain[cat["domain"]].append(deck_card_html(deck, cat, url, show_notion_tag=True))
        if notion_id in cards_by_notion:
            cards_by_notion[notion_id].append(deck_card_html(deck, cat, url, show_notion_tag=True))

    (ROOT / "search-index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    # 1) Notion 3.3 人資管理架構區塊
    notion_nav = "".join(
        f'<a class="n-pill" href="#n-{esc(n["id"])}"><b>{esc(n["code"])}</b> {esc(n["name"].replace(n["code"]+" ", ""))} '
        f'<small>({len(cards_by_notion[n["id"]])})</small></a>'
        for n in notion_list
    )
    notion_sections = []
    for n in notion_list:
        cs = cards_by_notion[n["id"]]
        subs_html = "".join(
            f'<span class="subpill{" active" if sub in active_notion_subs else ""}">{esc(sub)}</span>'
            for sub in n.get("subs", [])
        )
        body = "".join(cs) if cs else '<div class="soon">規劃中（已建立 Notion 3.3 標準子模組槽位，後續資料擴充後自動掛載）</div>'
        notion_sections.append(
            f'<section class="domain notion-sec" id="n-{esc(n["id"])}" data-notion="{esc(n["name"])}">'
            f'<div class="dhead"><span class="ncode">{esc(n["code"])}</span>'
            f'<h3>{esc(n["name"].replace(n["code"]+" ", ""))}</h3>'
            f'<p>{esc(n["desc"])}</p><span class="count">{len(cs)} 份</span></div>'
            f'<div class="subpills">{subs_html}</div>'
            f'<div class="decks">{body}</div></section>'
        )

    # 2) 原主題領域分類區塊（完整保留）
    classic_sections = []
    for d in catalog["domains"]:
        cs = cards_by_domain[d["id"]]
        body = "".join(cs) if cs else '<div class="soon">規劃中 · 資料擴充後將於此出現</div>'
        classic_sections.append(
            f'<section class="domain" data-domain="{esc(d["name"])}"><div class="dhead"><h3>{esc(d["name"])}</h3>'
            f'<p>{esc(d["desc"])}</p><span class="count">{len(cs)} 份</span></div><div class="decks">{body}</div></section>'
        )

    nd, ns = len(catalog["decks"]), len(index)
    home = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>人力資源管理知識庫</title><link rel="stylesheet" href="assets/style.css"></head>
<body class="homepage">
<header class="hero"><div class="wrap"><div class="kicker light">HR KNOWLEDGE BASE · NOTION 3.3 ARCHITECTURE</div>
<h1>人力資源管理知識庫</h1>
<p>{esc(catalog.get("tagline"))}</p>
<div class="searchbox"><input id="q" type="search" placeholder="輸入關鍵字，例如：斜率、耐力、鋼琴家、選才、薪酬、績效、OKR…" autofocus autocomplete="off">
<div class="chips" id="chips"></div></div>
<div class="stats"><div><b>{nd}</b>份導讀簡報</div><div><b>{ns}</b>筆可搜尋內容</div><div><b>{len(notion_list)}</b>大 Notion 3.3 模組</div><div><b>{len(catalog["domains"])}</b>個原主題分類</div></div></div></header>
<main class="wrap"><div id="results" class="results hidden"></div>
<div id="map">
<div class="mapbar">
  <h2 class="maptitle">知識地圖 <small>支援雙軌架構切換，點選書籍進入 10 分鐘導讀簡報</small></h2>
  <div class="viewswitch" role="tablist">
    <button id="vNotion" class="on" data-view="notion">Notion「3.3 人資管理」架構</button>
    <button id="vClassic" data-view="classic">原主題領域分類</button>
  </div>
</div>
<div id="view-notion">
  <div class="notion-banner"><div class="nb-title">3.3 人資管理全貌快速導覽</div><div class="nb-pills">{notion_nav}</div></div>
  {"".join(notion_sections)}
</div>
<div id="view-classic" class="hidden">
  {"".join(classic_sections)}
</div>
</div></main>
<footer class="wrap foot2">內容依各書原文與解讀來源整理；來源未載之處標註「原文未載」。雙軌分類支援 Notion「3.3 人資管理」與原主題架構。更新：{esc(catalog.get("updated"))}</footer>
<script src="assets/search.js"></script></body></html>'''
    (ROOT / "index.html").write_text(home, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("")
    print(f"built {nd} decks, {ns} index entries, {len(notion_list)} notion modules, {len(catalog['domains'])} classic domains")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
