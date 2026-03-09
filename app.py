"""
Monitor Deportivo Pro — Streamlit Edition v1.0
Adaptación del UserScript para correr como app web local con Streamlit.

Instalar dependencias:
    pip install streamlit anthropic requests beautifulsoup4 lxml

Correr:
    streamlit run app.py
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import unicodedata
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import anthropic

# ─── CONFIG ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor Deportivo Pro",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

MAX_ITEMS = 50
SIMILITUD_UMBRAL = 0.22

# ─── FUENTES ──────────────────────────────────────────────────────────────────
FUENTES_NAC = [
    {"id": "ole",           "nombre": "Olé",           "url": "https://www.ole.com.ar/",                             "color": "#00a846", "es_ole": True},
    {"id": "espn",          "nombre": "ESPN AR",        "url": "https://www.espn.com.ar/",                            "color": "#cc0000"},
    {"id": "tyc",           "nombre": "TyC Sports",     "url": "https://www.tycsports.com/",                          "color": "#1565c0"},
    {"id": "infobae",       "nombre": "Infobae",        "url": "https://www.infobae.com/deportes/",                   "color": "#b00020"},
    {"id": "lanacion",      "nombre": "La Nación",      "url": "https://www.lanacion.com.ar/deportes/",               "color": "#1565c0"},
    {"id": "tn",            "nombre": "TN Deportes",    "url": "https://tn.com.ar/deportes/",                         "color": "#cc2200"},
    {"id": "clarin",        "nombre": "Clarín Dep.",    "url": "https://www.clarin.com/deportes/",                    "color": "#c00000"},
    {"id": "elgrafico",     "nombre": "El Gráfico",     "url": "https://www.elgrafico.com.ar/",                       "color": "#b07800"},
    {"id": "dobleamarilla", "nombre": "Doble Amarilla", "url": "https://www.dobleamarilla.com.ar/",                   "color": "#a07800"},
    {"id": "bolavip",       "nombre": "Bolavip",        "url": "https://bolavip.com/ar",                              "color": "#c04a00"},
    {"id": "lavoz",         "nombre": "La Voz",         "url": "https://www.lavoz.com.ar/deportes/",                  "color": "#8b0000"},
    {"id": "cielo",         "nombre": "Cielo Sports",   "url": "https://infocielo.com/cielosports",                   "color": "#0077bb"},
    {"id": "capital",       "nombre": "La Capital",     "url": "https://www.lacapital.com.ar/secciones/ovacion.html", "color": "#6a0d8a"},
    {"id": "pagina12",      "nombre": "Página 12",      "url": "https://www.pagina12.com.ar/secciones/deportes",      "color": "#1a1a6e"},
    {"id": "ambito",        "nombre": "Ámbito Dep.",    "url": "https://www.ambito.com/deportes",                     "color": "#006633"},
    {"id": "na",            "nombre": "Noticias Arg.",  "url": "https://noticiasargentinas.com/search?category=65552a2ae38b1d41233b1aac", "color": "#c00060"},
]

FUENTES_INT = [
    {"id": "as",        "nombre": "AS",              "url": "https://as.com/",                                 "color": "#b00020"},
    {"id": "marca",     "nombre": "Marca",            "url": "https://www.marca.com/",                          "color": "#267326"},
    {"id": "mundodep",  "nombre": "Mundo Deportivo",  "url": "https://www.mundodeportivo.com/",                 "color": "#1565c0"},
    {"id": "sport",     "nombre": "Sport",            "url": "https://www.sport.es/es/",                        "color": "#cc0020"},
    {"id": "globo",     "nombre": "Globoesporte",     "url": "https://ge.globo.com/",                           "color": "#007a2f"},
    {"id": "lance",     "nombre": "Lance!",           "url": "https://lance.com.br/feed/",                      "color": "#005bac", "es_rss": True},
    {"id": "placar",    "nombre": "Placar",           "url": "https://placar.com.br/feed/",                     "color": "#c00040", "es_rss": True},
    {"id": "tmw",       "nombre": "TuttoMercato",     "url": "https://www.tuttomercatoweb.com/",                "color": "#003399"},
    {"id": "corriere",  "nombre": "Corriere Sport",   "url": "https://www.corrieredellosport.it/calcio",        "color": "#e06000"},
    {"id": "record",    "nombre": "Record PT",        "url": "https://www.record.pt/futebol/",                  "color": "#c8000a"},
    {"id": "sky",       "nombre": "Sky Sports",       "url": "https://www.skysports.com/rss/12040",             "color": "#0066cc", "es_rss": True},
    {"id": "goal",      "nombre": "Goal",             "url": "https://www.goal.com/es",                         "color": "#00a878"},
    {"id": "espnint",   "nombre": "ESPN INT",         "url": "https://www.espn.com/soccer/",                    "color": "#d00000"},
    {"id": "cbssport",  "nombre": "CBS Sports",       "url": "https://www.cbssports.com/rss/headlines/soccer/", "color": "#004b87", "es_rss": True},
    {"id": "sportnews", "nombre": "Sporting News",    "url": "https://www.sportingnews.com/us/soccer",          "color": "#cc3300"},
    {"id": "lequipe",   "nombre": "L'Equipe",         "url": "https://www.lequipe.fr/Football/",                "color": "#f5c400"},
    {"id": "uefa",      "nombre": "UEFA (RSS)",       "url": "https://www.uefa.com/rss/uefachampionsleague/rss.xml", "color": "#003087", "es_rss": True},
    {"id": "fifa",      "nombre": "FIFA (RSS)",       "url": "https://www.fifa.com/rss-feeds/index.html",       "color": "#326295"},
]

TODAS_FUENTES = FUENTES_NAC + FUENTES_INT
FUENTES_NAC_IDS = {f["id"] for f in FUENTES_NAC}

# ─── STOPWORDS ────────────────────────────────────────────────────────────────
STOPWORDS = set([
    "de","la","el","en","y","a","los","del","se","las","por","un","para","con","una","su","al","lo",
    "como","más","pero","sus","le","ya","o","fue","este","ha","si","porque","esta","son","entre",
    "cuando","muy","sin","sobre","también","me","hasta","hay","donde","quien","desde","todo","nos",
    "durante","e","esto","mi","antes","yo","otro","otras","otra","él","bien","así","cada","ser",
    "tiene","había","era","no","es","que","the","a","an","and","or","but","in","on","at","to","for",
    "of","with","by","from","is","was","are","were","be","been","have","has","had","will","would",
    "could","should","may","might","can","da","do","em","para","com","por","que","um","uma",
    "os","as","ao","na","no","nas","nos","se","seu","sua","seus","suas","não","após","tras",
    "vs","vs.","after","over","into","than","then","their","they","this","that",
])

# ─── SIMILITUD SEMÁNTICA ──────────────────────────────────────────────────────
def normalizar_titulo(titulo: str) -> set:
    t = titulo.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return {w for w in t.split() if len(w) > 3 and w not in STOPWORDS}

def similitud_jaccard(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    interseccion = len(set_a & set_b)
    union = len(set_a | set_b)
    return interseccion / union if union > 0 else 0.0

def es_exclusivo(titulo: str, propio_id: str, resultados: dict) -> bool:
    keys = normalizar_titulo(titulo)
    if len(keys) < 2:
        return False
    for f in TODAS_FUENTES:
        if f["id"] == propio_id:
            continue
        for n in resultados.get(f["id"], []):
            if similitud_jaccard(keys, normalizar_titulo(n["titulo"])) >= SIMILITUD_UMBRAL:
                return False
    return True

def analizar_ole_vs_competencia(resultados: dict) -> dict:
    # Pre-calcular keysets
    keysets = {}
    for f in TODAS_FUENTES:
        keysets[f["id"]] = [
            {"noticia": n, "keys": normalizar_titulo(n["titulo"])}
            for n in resultados.get(f["id"], [])
        ]

    ole_items = keysets.get("ole", [])
    competencia = [f for f in TODAS_FUENTES if not f.get("es_ole")]

    # 1. Exclusivos Olé
    exclusivos_ole = []
    for item in ole_items:
        encontrado = any(
            similitud_jaccard(item["keys"], ci["keys"]) >= SIMILITUD_UMBRAL
            for fid, citems in keysets.items()
            if fid != "ole"
            for ci in citems
        )
        if not encontrado:
            exclusivos_ole.append(item["noticia"])

    # 2. Faltantes en Olé
    faltantes_en_ole = []
    ya_agregados_keys = []
    for fuente in competencia:
        for item in keysets.get(fuente["id"], []):
            # ¿Lo tiene Olé?
            tiene_ole = any(
                similitud_jaccard(item["keys"], oi["keys"]) >= SIMILITUD_UMBRAL
                for oi in ole_items
            )
            if not tiene_ole:
                # Deduplicar entre faltantes
                es_dup = any(
                    similitud_jaccard(item["keys"], k) >= SIMILITUD_UMBRAL
                    for k in ya_agregados_keys
                )
                if not es_dup:
                    ya_agregados_keys.append(item["keys"])
                    faltantes_en_ole.append({
                        "titulo": item["noticia"]["titulo"],
                        "url": item["noticia"].get("url"),
                        "fuente_id": fuente["id"],
                        "fuente_nombre": fuente["nombre"],
                        "fuente_color": fuente["color"],
                    })

    # 3. Cubiertos por ambos
    cubiertos_por_ambos = []
    for item in ole_items:
        competidores = []
        for fid, citems in keysets.items():
            if fid == "ole":
                continue
            for ci in citems:
                sim = similitud_jaccard(item["keys"], ci["keys"])
                if sim >= SIMILITUD_UMBRAL:
                    competidores.append({"fuente_id": fid, "noticia": ci["noticia"], "sim": sim})
                    break
        if competidores:
            cubiertos_por_ambos.append({
                "noticia_ole": item["noticia"],
                "competencia": competidores[:4],
            })

    return {
        "exclusivos_ole": exclusivos_ole,
        "faltantes_en_ole": faltantes_en_ole,
        "cubiertos_por_ambos": cubiertos_por_ambos,
    }

def calcular_tendencias(resultados: dict) -> list:
    todas = []
    for f in TODAS_FUENTES:
        for n in resultados.get(f["id"], []):
            todas.append({"noticia": n, "fuente": f, "keys": normalizar_titulo(n["titulo"])})

    UMBRAL_CLUSTER = 0.20
    clusters = []
    asignado = [False] * len(todas)

    for i in range(len(todas)):
        if asignado[i]:
            continue
        cluster = {
            "titulo": todas[i]["noticia"]["titulo"],
            "url": todas[i]["noticia"].get("url"),
            "fuente_ids": {todas[i]["fuente"]["id"]},
            "noticias": [{"noticia": todas[i]["noticia"], "fuente": todas[i]["fuente"]}],
            "keys": todas[i]["keys"],
        }
        asignado[i] = True
        for j in range(i + 1, len(todas)):
            if asignado[j]:
                continue
            if similitud_jaccard(cluster["keys"], todas[j]["keys"]) >= UMBRAL_CLUSTER:
                cluster["fuente_ids"].add(todas[j]["fuente"]["id"])
                cluster["noticias"].append({"noticia": todas[j]["noticia"], "fuente": todas[j]["fuente"]})
                asignado[j] = True
        if len(cluster["fuente_ids"]) >= 2:
            clusters.append(cluster)

    clusters.sort(key=lambda c: (-len(c["fuente_ids"]), -len(c["noticias"])))
    return [
        {
            "titulo": c["titulo"],
            "url": c["url"],
            "cant_medios": len(c["fuente_ids"]),
            "fuente_ids": list(c["fuente_ids"]),
            "noticias": c["noticias"],
            "tiene_ole": "ole" in c["fuente_ids"],
            "nac": sum(1 for n in c["noticias"] if n["fuente"]["id"] in FUENTES_NAC_IDS),
            "intl": sum(1 for n in c["noticias"] if n["fuente"]["id"] not in FUENTES_NAC_IDS),
        }
        for c in clusters
    ]

def analizar_ole_vs_compecencia_safe(resultados: dict) -> dict:
    """Wrapper seguro para el análisis semántico."""
    try:
        return analizar_ole_vs_competencia(resultados)
    except Exception as e:
        return {"exclusivos_ole": [], "faltantes_en_ole": [], "cubiertos_por_ambos": []}

# ─── EXTRACCIÓN HTML ──────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DepMonitorPro/10.0)"}

def extraer_rss(xml_text: str) -> list:
    noticias, vistos = [], set()
    try:
        soup = BeautifulSoup(xml_text, "xml")
        for item in soup.find_all(["item", "entry"])[:MAX_ITEMS]:
            titulo_tag = item.find("title")
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            titulo = re.sub(r"<[^>]+>", "", titulo)
            titulo = titulo.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"').replace("&#39;","'")
            if not titulo or len(titulo) < 15 or len(titulo) > 300 or titulo in vistos:
                continue
            vistos.add(titulo)
            url = None
            link_tag = item.find("link")
            if link_tag:
                url = link_tag.get_text(strip=True) or link_tag.get("href")
            if not url or not url.startswith("http"):
                guid = item.find("guid", isPermaLink="true")
                url = guid.get_text(strip=True) if guid else None
            noticias.append({"titulo": titulo, "url": url})
    except Exception:
        pass
    return noticias[:MAX_ITEMS]

def extraer_generico(html: str, fuente: dict) -> list:
    if fuente.get("es_rss"):
        return extraer_rss(html)

    soup = BeautifulSoup(html, "html.parser")
    base_url = re.match(r"https?://[^/]+", fuente["url"])
    base = base_url.group(0) if base_url else ""
    noticias, vistos = [], set()

    CARD_SELS = ["article", "[class*=card]", "[class*=story]", "[class*=nota]", "[class*=item]", "[class*=news]"]
    TITLE_SELS = ["h1","h2","h3","h4","[class*=title]","[class*=headline]","[class*=titular]"]

    def resolve_url(href):
        if not href or href.startswith("javascript") or href == "#":
            return None
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return base + href
        if href.startswith("http"):
            return href
        return None

    def get_titulo(el):
        for sel in TITLE_SELS:
            t = el.select_one(sel)
            if t:
                return t.get_text(strip=True)
        return None

    def get_url(el, titulo_el):
        link = titulo_el.find_parent("a") or titulo_el.find("a") or el.find("a")
        if link:
            return resolve_url(link.get("href", ""))
        return None

    # Intentar cards
    for sel in CARD_SELS:
        for card in soup.select(sel)[:MAX_ITEMS * 2]:
            if len(noticias) >= MAX_ITEMS:
                break
            titulo_el = None
            for tsel in TITLE_SELS:
                titulo_el = card.select_one(tsel)
                if titulo_el:
                    break
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            if len(titulo) < 20 or len(titulo) > 300 or titulo in vistos:
                continue
            vistos.add(titulo)
            url = get_url(card, titulo_el)
            noticias.append({"titulo": titulo, "url": url})

    # Fallback: sólo headings
    if len(noticias) < 8:
        for sel in ["h2","h3"]:
            for el in soup.select(sel)[:MAX_ITEMS * 2]:
                if len(noticias) >= MAX_ITEMS:
                    break
                titulo = el.get_text(strip=True)
                if len(titulo) < 20 or len(titulo) > 300 or titulo in vistos:
                    continue
                vistos.add(titulo)
                link = el.find_parent("a") or el.find("a")
                url = resolve_url(link.get("href", "")) if link else None
                noticias.append({"titulo": titulo, "url": url})

    return noticias[:MAX_ITEMS]

def fetch_fuente(fuente: dict) -> dict:
    try:
        resp = requests.get(fuente["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        noticias = extraer_generico(resp.text, fuente)
        return {"id": fuente["id"], "noticias": noticias, "error": None}
    except Exception as e:
        return {"id": fuente["id"], "noticias": [], "error": str(e)}

# ─── IA — CLAUDE ──────────────────────────────────────────────────────────────
def call_claude(prompt: str, api_key: str, max_tokens: int = 2000) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text

def prompt_analisis_general(resultados: dict) -> str:
    bloque = "\n\n".join(
        f"### {f['nombre']}\n" + "\n".join(
            f"  • {n['titulo']}"
            for n in resultados.get(f["id"], [])[:25]
        ) or "  (sin datos)"
        for f in TODAS_FUENTES
    )
    return f"""Sos editor jefe de un portal deportivo argentino. Analizá estos titulares de {len(TODAS_FUENTES)} medios deportivos y respondé en español rioplatense:

1. AGENDA DEL MOMENTO — 4 oraciones sobre qué temas dominan ahora.
2. TEMAS CON MAYOR VOLUMEN — Los 5 temas que más medios cubren simultáneamente.
3. OPORTUNIDADES EDITORIALES — 3 ideas de notas que nadie cubre bien pero tienen potencial.
4. DIFERENCIAS NACIONALES vs INTERNACIONALES — Qué cubren los medios españoles/brasileños/ingleses que los argentinos ignoran, y viceversa.

Separar secciones con ───────. Sé directo y accionable.

{bloque}"""

def prompt_informe_ole(resultados: dict, analisis: dict) -> str:
    exclusivos = analisis["exclusivos_ole"]
    faltantes = analisis["faltantes_en_ole"]
    compartidos = analisis["cubiertos_por_ambos"]

    bloque_excl = "\n".join(f"  • {n['titulo']}" for n in exclusivos[:30]) or "  (ninguno)"
    bloque_falt = "\n".join(f"  • [{f['fuente_nombre']}] {f['titulo']}" for f in faltantes[:40]) or "  (ninguno)"
    bloque_comp = "\n\n".join(
        f"  • OLÉ: \"{c['noticia_ole']['titulo']}\"\n" +
        "\n".join(
            f"    → [{TODAS_FUENTES[[x['id'] for x in TODAS_FUENTES].index(comp['fuente_id'])]['nombre'] if comp['fuente_id'] in [x['id'] for x in TODAS_FUENTES] else comp['fuente_id']}] {comp['noticia']['titulo']}"
            for comp in c["competencia"]
        )
        for c in compartidos[:20]
    ) or "  (ninguno)"

    return f"""Sos editor jefe de Olé. Tenés un análisis semántico automático que agrupó noticias por TEMA (no por título exacto).

⚠️ Si un tema figura en "FALTANTES", es porque verdaderamente no está en Olé.

─────────────────────────────────────────────────────
## EXCLUSIVOS DE OLÉ ({len(exclusivos)} temas):
{bloque_excl}

─────────────────────────────────────────────────────
## FALTANTES EN OLÉ ({len(faltantes)} temas):
{bloque_falt}

─────────────────────────────────────────────────────
## TEMAS COMPARTIDOS CON ÁNGULO DIFERENTE:
{bloque_comp}
─────────────────────────────────────────────────────

Generá un informe editorial en español rioplatense:

1. 🟢 DONDE OLÉ ESTÁ ADELANTE — 5 exclusivos más valiosos.
2. 🔴 LO QUE OLÉ NO DIO — TOP 5 urgentes con título sugerido y ángulo para Argentina.
3. 🔵 MISMO TEMA, MEJOR ÁNGULO — 3 casos donde la competencia lo enfocó mejor.
4. ⚡ ALERTAS INTERNACIONALES — Top 3 noticias europeas/brasileñas con potencial para Olé.
5. 📋 PLAN EDITORIAL — 4 acciones prioritarias para las próximas 3 horas.

Separar secciones con ───────. Sé muy específico y accionable."""

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "resultados" not in st.session_state:
    st.session_state.resultados = {}
if "ultima_act" not in st.session_state:
    st.session_state.ultima_act = None
if "analisis_general" not in st.session_state:
    st.session_state.analisis_general = ""
if "informe_ole" not in st.session_state:
    st.session_state.informe_ole = ""
if "ole_analisis" not in st.session_state:
    st.session_state.ole_analisis = None
if "tendencias" not in st.session_state:
    st.session_state.tendencias = []
if "image_cache" not in st.session_state:
    st.session_state.image_cache = {}  # url -> og:image url or ""

# ─── IMÁGENES OG ─────────────────────────────────────────────────────────────
def fetch_og_image(url: str) -> str:
    """Busca el og:image o twitter:image de una URL. Retorna la URL de la imagen o ''."""
    if not url or not url.startswith("http"):
        return ""
    cached = st.session_state.image_cache.get(url)
    if cached is not None:
        return cached
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        img = (
            soup.find("meta", property="og:image") or
            soup.find("meta", attrs={"name": "twitter:image"}) or
            soup.find("meta", attrs={"name": "og:image"})
        )
        result = img.get("content", "") if img else ""
        st.session_state.image_cache[url] = result
        return result
    except Exception:
        st.session_state.image_cache[url] = ""
        return ""

def fetch_og_images_batch(noticias: list) -> dict:
    """Fetch og:images en paralelo para una lista de noticias. Retorna {url: img_url}."""
    urls_sin_cache = [
        n["url"] for n in noticias
        if n.get("url") and st.session_state.image_cache.get(n["url"]) is None
    ]
    if urls_sin_cache:
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(fetch_og_image, u): u for u in urls_sin_cache}
            for f in as_completed(futures):
                f.result()  # los resultados ya quedan en image_cache
    return st.session_state.image_cache

def render_news_cards(noticias: list, fuente: dict, resultados: dict, cols_per_row: int = 3):
    """
    Renderiza noticias como cards con imagen grande arriba del título.
    Descarga og:images en paralelo antes de renderizar.
    """
    if not noticias:
        st.warning("Sin datos para esta fuente.")
        return

    # Fetch de imágenes en batch (solo las que no están en cache)
    with st.spinner("Cargando imágenes..."):
        fetch_og_images_batch(noticias)

    # Render en grilla
    rows = [noticias[i:i+cols_per_row] for i in range(0, len(noticias), cols_per_row)]
    color = fuente["color"]

    for row in rows:
        cols = st.columns(cols_per_row)
        for col, n in zip(cols, row):
            with col:
                img_url = st.session_state.image_cache.get(n.get("url", ""), "")
                excl = es_exclusivo(n["titulo"], fuente["id"], resultados)

                # Card HTML completa
                excl_badge = (
                    f'<div style="position:absolute;top:8px;left:8px;'
                    f'background:rgba(212,160,23,.92);color:#fff;'
                    f'font-size:10px;font-weight:700;padding:2px 8px;'
                    f'border-radius:3px;letter-spacing:.6px">★ EXCLUSIVO</div>'
                ) if excl else ""

                img_html = (
                    f'<div style="position:relative;width:100%;padding-bottom:52%;'
                    f'overflow:hidden;background:#eef0f5;border-radius:8px 8px 0 0">'
                    f'<img src="{img_url}" style="position:absolute;inset:0;width:100%;'
                    f'height:100%;object-fit:cover" onerror="this.style.display=\'none\'">'
                    f'{excl_badge}</div>'
                ) if img_url else (
                    f'<div style="width:100%;padding:28px 0;background:#eef0f5;'
                    f'border-radius:8px 8px 0 0;text-align:center;font-size:28px">⚽</div>'
                )

                border_color = "#d4a017" if excl else color
                bg_excl = "background:#fffdf4;" if excl else ""

                titulo_link = (
                    f'<a href="{n["url"]}" target="_blank" rel="noopener" '
                    f'style="color:#14171a;text-decoration:none;font-size:13.5px;'
                    f'font-weight:600;line-height:1.5;display:block">'
                    f'{n["titulo"]}</a>'
                ) if n.get("url") else (
                    f'<span style="color:#14171a;font-size:13.5px;font-weight:600;'
                    f'line-height:1.5">{n["titulo"]}</span>'
                )

                fuente_tag = (
                    f'<span style="font-size:10px;font-weight:700;color:{color};'
                    f'font-family:sans-serif;letter-spacing:.6px;text-transform:uppercase">'
                    f'{fuente["nombre"]}</span>'
                )

                card_html = f"""
                <div style="border:1px solid #dde1ea;border-left:3px solid {border_color};
                     border-radius:8px;overflow:hidden;margin-bottom:4px;{bg_excl}
                     box-shadow:0 1px 4px rgba(0,0,0,.07)">
                  {img_html}
                  <div style="padding:10px 12px 12px">
                    {fuente_tag}
                    <div style="margin-top:5px">{titulo_link}</div>
                  </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 Monitor Deportivo Pro")
    st.markdown(f"**{len(TODAS_FUENTES)} medios** · {len(FUENTES_NAC)} nac + {len(FUENTES_INT)} int")
    st.divider()

    api_key = st.text_input(
        "🔑 Anthropic API Key",
        type="password",
        placeholder="sk-ant-api03-...",
        help="Necesaria solo para el análisis IA. Los feeds se cargan sin API key.",
    )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        solo_nac = st.checkbox("Solo nacionales", value=False)
    with col_b:
        solo_int = st.checkbox("Solo int.", value=False)

    if st.button("↺ Actualizar fuentes", type="primary", use_container_width=True):
        fuentes_a_cargar = TODAS_FUENTES
        if solo_nac:
            fuentes_a_cargar = FUENTES_NAC
        elif solo_int:
            fuentes_a_cargar = FUENTES_INT

        progress = st.progress(0, text="Cargando medios...")
        resultados_nuevos = {}
        errores = []
        total = len(fuentes_a_cargar)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_fuente, f): f for f in fuentes_a_cargar}
            done = 0
            for future in as_completed(futures):
                res = future.result()
                resultados_nuevos[res["id"]] = res["noticias"]
                if res["error"]:
                    errores.append(f"{res['id']}: {res['error']}")
                done += 1
                progress.progress(done / total, text=f"Cargando... {done}/{total}")

        st.session_state.resultados = resultados_nuevos
        st.session_state.ultima_act = datetime.now()
        st.session_state.ole_analisis = analizar_ole_vs_compecencia_safe(resultados_nuevos)
        st.session_state.tendencias = calcular_tendencias(resultados_nuevos)
        progress.empty()

        total_noticias = sum(len(v) for v in resultados_nuevos.values())
        st.success(f"✔ {total_noticias} noticias de {total} medios")
        if errores:
            with st.expander(f"⚠ {len(errores)} errores"):
                st.text("\n".join(errores))
        st.rerun()

    if st.session_state.ultima_act:
        st.caption(f"Última actualización: {st.session_state.ultima_act.strftime('%H:%M:%S')}")
        total_noticias = sum(len(v) for v in st.session_state.resultados.values())
        st.metric("Total de noticias", total_noticias)

    st.divider()
    st.markdown("**IA con Claude**")

    if st.button("✦ Análisis General", use_container_width=True):
        if not api_key:
            st.error("Ingresá tu API key")
        elif not st.session_state.resultados:
            st.error("Actualizá las fuentes primero")
        else:
            with st.spinner("Analizando con Claude..."):
                try:
                    prompt = prompt_analisis_general(st.session_state.resultados)
                    st.session_state.analisis_general = call_claude(prompt, api_key, 1800)
                    st.success("✔ Análisis generado")
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.button("🟢 Informe Olé IA", use_container_width=True):
        if not api_key:
            st.error("Ingresá tu API key")
        elif not st.session_state.resultados:
            st.error("Actualizá las fuentes primero")
        else:
            analisis = st.session_state.ole_analisis or analizar_ole_vs_compecencia_safe(st.session_state.resultados)
            with st.spinner("Generando informe Olé..."):
                try:
                    prompt = prompt_informe_ole(st.session_state.resultados, analisis)
                    st.session_state.informe_ole = call_claude(prompt, api_key, 2400)
                    st.success("✔ Informe generado")
                except Exception as e:
                    st.error(f"Error: {e}")





# ─── MAIN ─────────────────────────────────────────────────────────────────────
st.title("📡 Monitor Deportivo Pro")

if not st.session_state.resultados:
    st.info("👈 Hacé clic en **↺ Actualizar fuentes** en el panel izquierdo para comenzar.")
    st.stop()

resultados = st.session_state.resultados
ole_analisis = st.session_state.ole_analisis
tendencias = st.session_state.tendencias

# ─── TABS PRINCIPALES ────────────────────────────────────────────────────────
tab_nac, tab_int, tab_ole, tab_tend, tab_ia = st.tabs([
    f"🇦🇷 Nacionales ({sum(len(resultados.get(f['id'],[])) for f in FUENTES_NAC)})",
    f"🌍 Internacionales ({sum(len(resultados.get(f['id'],[])) for f in FUENTES_INT)})",
    "⭐ Olé vs Todos",
    f"📊 Tendencias ({len(tendencias)})",
    "🤖 Análisis IA",
])

# ─── TAB NACIONALES ──────────────────────────────────────────────────────────
with tab_nac:
    fuente_sel = st.selectbox(
        "Medio",
        [f["nombre"] for f in FUENTES_NAC],
        key="sel_nac",
    )
    fuente_obj = next(f for f in FUENTES_NAC if f["nombre"] == fuente_sel)
    noticias = resultados.get(fuente_obj["id"], [])

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(
            f'<span style="color:{fuente_obj["color"]};font-weight:700;font-size:18px">'
            f'{fuente_obj["nombre"]}</span> — {len(noticias)} noticias',
            unsafe_allow_html=True,
        )
    with col_h2:
        cols_per_row = st.selectbox("Columnas", [2, 3, 4], index=1, key="cols_nac")

    filtro = st.text_input("🔍 Filtrar por palabra", key="filtro_nac")
    lista = [n for n in noticias if filtro.lower() in n["titulo"].lower()] if filtro else noticias

    render_news_cards(lista, fuente_obj, resultados, cols_per_row=cols_per_row)

# ─── TAB INTERNACIONALES ─────────────────────────────────────────────────────
with tab_int:
    fuente_sel_i = st.selectbox(
        "Medio",
        [f["nombre"] for f in FUENTES_INT],
        key="sel_int",
    )
    fuente_obj_i = next(f for f in FUENTES_INT if f["nombre"] == fuente_sel_i)
    noticias_i = resultados.get(fuente_obj_i["id"], [])

    col_h1i, col_h2i = st.columns([3, 1])
    with col_h1i:
        st.markdown(
            f'<span style="color:{fuente_obj_i["color"]};font-weight:700;font-size:18px">'
            f'{fuente_obj_i["nombre"]}</span> — {len(noticias_i)} noticias',
            unsafe_allow_html=True,
        )
    with col_h2i:
        cols_per_row_i = st.selectbox("Columnas", [2, 3, 4], index=1, key="cols_int")

    filtro_i = st.text_input("🔍 Filtrar por palabra", key="filtro_int")
    lista_i = [n for n in noticias_i if filtro_i.lower() in n["titulo"].lower()] if filtro_i else noticias_i

    render_news_cards(lista_i, fuente_obj_i, resultados, cols_per_row=cols_per_row_i)

# ─── TAB OLÉ VS TODOS ────────────────────────────────────────────────────────
with tab_ole:
    if not ole_analisis:
        st.info("Actualizá las fuentes para ver el análisis semántico.")
    else:
        excl = ole_analisis["exclusivos_ole"]
        falt = ole_analisis["faltantes_en_ole"]
        comp = ole_analisis["cubiertos_por_ambos"]

        c1, c2, c3 = st.columns(3)
        c1.metric("⭐ Exclusivos Olé", len(excl), help="Temas que solo cubre Olé")
        c2.metric("❌ Ausentes en Olé", len(falt), help="Temas que tiene la competencia y Olé NO cubre")
        c3.metric("🔄 Temas compartidos", len(comp), help="Cubiertos por ambos, posible ángulo diferente")

        st.divider()

        sub1, sub2, sub3 = st.tabs([
            f"⭐ Exclusivos Olé ({len(excl)})",
            f"❌ Faltantes ({len(falt)})",
            f"🔄 Compartidos ({len(comp)})",
        ])

        with sub1:
            if not excl:
                st.info("No se detectaron exclusivos.")
            for n in excl:
                if n.get("url"):
                    st.markdown(f"⭐ [{n['titulo']}]({n['url']})")
                else:
                    st.markdown(f"⭐ {n['titulo']}")

        with sub2:
            if not falt:
                st.success("✔ Olé cubre todos los temas detectados.")
            else:
                for f_item in falt:
                    col_hex = f_item["fuente_color"]
                    badge_html = (
                        f'<span style="background:{col_hex}22;color:{col_hex};border:1px solid {col_hex}55;'
                        f'padding:1px 8px;border-radius:4px;font-size:11px;font-weight:700">'
                        f'{f_item["fuente_nombre"]}</span>'
                    )
                    if f_item.get("url"):
                        st.markdown(
                            f'{badge_html} [{f_item["titulo"]}]({f_item["url"]})',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f'{badge_html} {f_item["titulo"]}',
                            unsafe_allow_html=True,
                        )

        with sub3:
            if not comp:
                st.info("Sin temas compartidos detectados.")
            for item in comp[:30]:
                nol = item["noticia_ole"]
                with st.expander(f"🔄 {nol['titulo'][:90]}..."):
                    if nol.get("url"):
                        st.markdown(f"**Olé:** [{nol['titulo']}]({nol['url']})")
                    else:
                        st.markdown(f"**Olé:** {nol['titulo']}")
                    for ci in item["competencia"]:
                        fobj = next((f for f in TODAS_FUENTES if f["id"] == ci["fuente_id"]), None)
                        nombre = fobj["nombre"] if fobj else ci["fuente_id"]
                        color = fobj["color"] if fobj else "#666"
                        badge = (
                            f'<span style="color:{color};font-weight:700;font-size:11px">{nombre}</span>'
                        )
                        if ci["noticia"].get("url"):
                            st.markdown(
                                f'{badge} [{ci["noticia"]["titulo"]}]({ci["noticia"]["url"]})',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(f'{badge} {ci["noticia"]["titulo"]}', unsafe_allow_html=True)

# ─── TAB TENDENCIAS ──────────────────────────────────────────────────────────
with tab_tend:
    if not tendencias:
        st.info("Actualizá las fuentes para ver las tendencias.")
    else:
        total_fuentes = len(TODAS_FUENTES)

        filtro_tend = st.radio(
            "Filtrar",
            ["Sin Olé ❌", "Con Olé ✅", "🔥 Hot (+20% medios)", "Todos"],
            horizontal=True,
            key="filtro_tend",
        )

        lista_tend = tendencias[:80]
        if filtro_tend == "Sin Olé ❌":
            lista_tend = [t for t in lista_tend if not t["tiene_ole"]]
        elif filtro_tend == "Con Olé ✅":
            lista_tend = [t for t in lista_tend if t["tiene_ole"]]
        elif filtro_tend == "🔥 Hot (+20% medios)":
            lista_tend = [t for t in lista_tend if t["cant_medios"] / total_fuentes >= 0.20]

        st.caption(f"{len(lista_tend)} temas · umbral similitud: {SIMILITUD_UMBRAL}")

        for t in lista_tend[:60]:
            pct = t["cant_medios"] / total_fuentes
            if pct >= 0.5:
                accent = "#dc2626"
                temp = "🔥🔥🔥"
            elif pct >= 0.30:
                accent = "#ea580c"
                temp = "🔥🔥"
            elif pct >= 0.15:
                accent = "#ca8a04"
                temp = "🔥"
            else:
                accent = "#3b82f6"
                temp = ""

            ole_badge = "✅ OLÉ" if t["tiene_ole"] else "❌ FALTA"
            ole_color = "#15803d" if t["tiene_ole"] else "#991b1b"

            with st.expander(
                f'{temp} {t["titulo"][:85]} — '
                f'**{t["cant_medios"]} medios** | '
                f'{t["nac"]}🇦🇷 {t["intl"]}🌍'
            ):
                st.markdown(
                    f'<span style="color:{ole_color};font-weight:700;background:{ole_color}15;'
                    f'padding:2px 10px;border-radius:4px">{ole_badge}</span>',
                    unsafe_allow_html=True,
                )
                st.write("")
                for item in t["noticias"]:
                    n = item["noticia"]
                    f = item["fuente"]
                    badge_html = (
                        f'<span style="color:{f["color"]};font-size:10px;font-weight:700;'
                        f'background:{f["color"]}15;padding:1px 7px;border-radius:3px">'
                        f'{f["nombre"]}</span>'
                    )
                    if n.get("url"):
                        st.markdown(
                            f'{badge_html} [{n["titulo"]}]({n["url"]})',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f'{badge_html} {n["titulo"]}', unsafe_allow_html=True)

# ─── TAB IA ──────────────────────────────────────────────────────────────────
with tab_ia:
    ia1, ia2, ia3 = st.tabs(["✦ Análisis General", "🟢 Informe Olé", "📋 Exclusivos (todos)"])

    with ia1:
        if st.session_state.analisis_general:
            st.text_area(
                "Análisis General",
                st.session_state.analisis_general,
                height=500,
                label_visibility="collapsed",
            )
            st.download_button(
                "📥 Descargar análisis",
                st.session_state.analisis_general,
                file_name="analisis_general.txt",
                mime="text/plain",
            )
        else:
            st.info("Hacé clic en **✦ Análisis General** en el panel izquierdo (requiere API key).")

    with ia2:
        if st.session_state.informe_ole:
            st.text_area(
                "Informe Olé",
                st.session_state.informe_ole,
                height=500,
                label_visibility="collapsed",
            )
            st.download_button(
                "📥 Descargar informe",
                st.session_state.informe_ole,
                file_name="informe_ole.txt",
                mime="text/plain",
            )
        else:
            st.info("Hacé clic en **🟢 Informe Olé IA** en el panel izquierdo (requiere API key).")

    with ia3:
        st.markdown(f"**Titulares únicos por tema** — similitud Jaccard < {SIMILITUD_UMBRAL}")
        exclusivos_todos = []
        for f in TODAS_FUENTES:
            for n in resultados.get(f["id"], []):
                if es_exclusivo(n["titulo"], f["id"], resultados):
                    exclusivos_todos.append({"fuente": f, "noticia": n})

        if not exclusivos_todos:
            st.info("No se detectaron exclusivos.")
        else:
            st.caption(f"{len(exclusivos_todos)} exclusivos detectados")
            for item in exclusivos_todos[:100]:
                f = item["fuente"]
                n = item["noticia"]
                badge = (
                    f'<span style="color:{f["color"]};font-weight:700;font-size:11px;'
                    f'background:{f["color"]}15;padding:1px 8px;border-radius:4px">'
                    f'{f["nombre"]}</span>'
                )
                if n.get("url"):
                    st.markdown(f'{badge} [{n["titulo"]}]({n["url"]})', unsafe_allow_html=True)
                else:
                    st.markdown(f'{badge} {n["titulo"]}', unsafe_allow_html=True)

# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"Monitor Deportivo Pro v1.0 (Streamlit) · "
    f"Similitud semántica Jaccard (umbral: {SIMILITUD_UMBRAL}) · "
    f"{len(TODAS_FUENTES)} medios"
)
