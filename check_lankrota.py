#!/usr/bin/env python3
"""
check_lankrota.py - Kontrollerar länkröta i Wikidata referenceURL för svenska grillplatser.
Genererar lankrota.html med färgkodad status för varje URL.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
import html
import sys

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT
  ?item
  ?itemLabel
  (SAMPLE(?referenceURL) AS ?grillplatserURL)
  (SAMPLE(?osm) AS ?osm)
  (SAMPLE(?naturkartan) AS ?naturkartan)
WHERE {
  ?item wdt:P1343 wd:Q120778083 .

  OPTIONAL {
    ?item p:P1343 ?statement .
    ?statement prov:wasDerivedFrom ?reference .
    ?reference pr:P854 ?referenceURL .
    FILTER(CONTAINS(STR(?referenceURL), "grillplatser.nu"))
  }

  OPTIONAL { ?item wdt:P11693 ?osm . }
  OPTIONAL { ?item wdt:P10467 ?naturkartan . }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "sv,en,mul" .
  }
}
GROUP BY ?item ?itemLabel
ORDER BY ?itemLabel
"""

ISSUE_URL = "https://github.com/salgo60/svenska-grillplatser/issues/2"


def run_sparql(query):
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    url = f"{SPARQL_ENDPOINT}?{params}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "svenska-grillplatser-lankrota-checker/1.0 (github.com/salgo60/svenska-grillplatser)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def check_url(url, timeout=10):
    """Returns (status_code_or_None, ok: bool, error_msg)"""
    if not url:
        return None, False, "Ingen URL"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "svenska-grillplatser-lankrota-checker/1.0",
                "Range": "bytes=0-0",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            return code, code in (200, 206) or (200 <= code < 400), ""
    except urllib.error.HTTPError as e:
        return e.code, False, str(e)
    except urllib.error.URLError as e:
        return None, False, str(e.reason)
    except Exception as e:
        return None, False, str(e)


def get_value(binding, key):
    return binding.get(key, {}).get("value", "")


def wikidata_item_url(item_uri):
    qid = item_uri.split("/")[-1]
    return f"https://www.wikidata.org/wiki/{qid}", qid


def generate_html(rows, generated_at):
    ok_count = sum(1 for r in rows if r["url_ok"])
    broken_count = sum(1 for r in rows if not r["url_ok"] and r["url"])
    no_url_count = sum(1 for r in rows if not r["url"])
    total = len(rows)

    lines = []
    lines.append("<!DOCTYPE html>")
    lines.append('<html lang="sv">')
    lines.append("<head>")
    lines.append('<meta charset="UTF-8">')
    lines.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    lines.append("<title>Länkröta-kontroll – Svenska Grillplatser (Wikidata)</title>")
    lines.append("""<style>
body { font-family: sans-serif; margin: 2rem; color: #222; }
h1 { margin-bottom: 0.2rem; }
.meta { color: #555; font-size: 0.9rem; margin-bottom: 1.5rem; }
.summary { margin-bottom: 1rem; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: bold; margin-right: 0.4rem; }
.badge-ok  { background: #d4edda; color: #155724; }
.badge-bad { background: #f8d7da; color: #721c24; }
.badge-nourl { background: #fff3cd; color: #856404; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th { background: #343a40; color: #fff; padding: 0.5rem 0.7rem; text-align: left; }
td { padding: 0.4rem 0.7rem; vertical-align: top; border-bottom: 1px solid #dee2e6; }
tr.ok   { background: #f0fff4; }
tr.bad  { background: #fff0f0; }
tr.nourl { background: #fffde7; }
.status-ok  { color: #155724; font-weight: bold; }
.status-bad { color: #721c24; font-weight: bold; }
.status-nourl { color: #856404; }
a { color: #0056b3; }
</style>""")
    lines.append("</head>")
    lines.append("<body>")
    lines.append("<h1>Länkröta-kontroll – Svenska Grillplatser (Wikidata)</h1>")
    lines.append(f'<p class="meta">Genererad: <strong>{html.escape(generated_at)}</strong> &nbsp;|&nbsp; '
                 f'<a href="{html.escape(ISSUE_URL)}">Issues på GitHub</a></p>')
    lines.append(f'<div class="summary">'
                 f'<span class="badge badge-ok">✅ OK: {ok_count}</span>'
                 f'<span class="badge badge-bad">❌ Länkröta: {broken_count}</span>'
                 f'<span class="badge badge-nourl">⚠️ Ingen URL: {no_url_count}</span>'
                 f'&nbsp; Totalt: {total}'
                 f'</div>')

    lines.append("<table>")
    lines.append("<thead><tr>"
                 "<th>#</th>"
                 "<th>Grillplats (Wikidata)</th>"
                 "<th>grillplatser.nu URL</th>"
                 "<th>HTTP-status</th>"
                 "<th>OSM</th>"
                 "<th>Naturkartan</th>"
                 "</tr></thead>")
    lines.append("<tbody>")

    for i, r in enumerate(rows, 1):
        if r["url_ok"]:
            row_class = "ok"
            status_class = "status-ok"
            status_text = f"✅ {r['status_code']}"
        elif r["url"]:
            row_class = "bad"
            status_class = "status-bad"
            status_text = f"❌ {r['status_code'] or ''} {html.escape(r['error'])}"
        else:
            row_class = "nourl"
            status_class = "status-nourl"
            status_text = "⚠️ Ingen URL"

        wd_url, qid = wikidata_item_url(r["item"])
        wd_link = f'<a href="{html.escape(wd_url)}" target="_blank">{html.escape(r["label"] or qid)}</a>'

        if r["url"]:
            grillplatser_link = f'<a href="{html.escape(r["url"])}" target="_blank">{html.escape(r["url"])}</a>'
        else:
            grillplatser_link = "<em>saknas</em>"

        osm_cell = ""
        if r["osm"]:
            osm_cell = f'<a href="https://www.openstreetmap.org/{html.escape(r["osm"])}" target="_blank">{html.escape(r["osm"])}</a>'

        nk_cell = ""
        if r["naturkartan"]:
            nk_cell = f'<a href="https://naturkartan.se/sv/{html.escape(r["naturkartan"])}" target="_blank">{html.escape(r["naturkartan"])}</a>'

        lines.append(
            f'<tr class="{row_class}">'
            f"<td>{i}</td>"
            f"<td>{wd_link}</td>"
            f"<td>{grillplatser_link}</td>"
            f'<td class="{status_class}">{status_text}</td>'
            f"<td>{osm_cell}</td>"
            f"<td>{nk_cell}</td>"
            f"</tr>"
        )

    lines.append("</tbody></table>")
    lines.append("</body></html>")
    return "\n".join(lines)


def main():
    print("Hämtar data från Wikidata SPARQL...", flush=True)
    data = run_sparql(SPARQL_QUERY)
    bindings = data["results"]["bindings"]
    print(f"Hittade {len(bindings)} poster.", flush=True)

    rows = []
    for i, b in enumerate(bindings, 1):
        item = get_value(b, "item")
        label = get_value(b, "itemLabel")
        url = get_value(b, "grillplatserURL")
        osm = get_value(b, "osm")
        naturkartan = get_value(b, "naturkartan")

        print(f"[{i}/{len(bindings)}] {label or item} -> {url or '(ingen URL)'}", end=" ", flush=True)
        status_code, ok, error = check_url(url)
        print(f"{'OK' if ok else 'FEL'} {status_code or ''}", flush=True)

        rows.append({
            "item": item,
            "label": label,
            "url": url,
            "url_ok": ok,
            "status_code": status_code,
            "error": error,
            "osm": osm,
            "naturkartan": naturkartan,
        })

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html_content = generate_html(rows, generated_at)

    out_file = "lankrota.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    broken = [r for r in rows if not r["url_ok"] and r["url"]]
    no_url = [r for r in rows if not r["url"]]
    print(f"\n✅ Rapport sparad till {out_file}")
    print(f"   OK: {len(rows) - len(broken) - len(no_url)}  |  Länkröta: {len(broken)}  |  Ingen URL: {len(no_url)}")


if __name__ == "__main__":
    main()
