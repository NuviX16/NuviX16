#!/usr/bin/env python3
"""Genera las tarjetas SVG del perfil (estadisticas y lenguajes) con la paleta Reze Sunset.

Lo ejecuta la GitHub Action .github/workflows/tarjetas.yml una vez al dia.
Para probarlo en local:  GITHUB_TOKEN=$(gh auth token) python3 scripts/tarjetas.py
"""
import json
import os
import urllib.request
from html import escape

USUARIO = os.environ.get("USUARIO", "NuviX16")
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tarjetas")

# Paleta Reze Sunset
C = {
    "fondo": "#100e0c", "borde": "#2a241f", "barra": "#1e1a16", "texto": "#efe4d4",
    "suave": "#bcae9e", "acento": "#e0a57a", "icono": "#c7b0d6",
}
COLORES_LENGUAJES = ["#e0a57a", "#c7b0d6", "#7fc4b0", "#f0b48a", "#e8b4b0", "#ecd29a", "#8fcfaa", "#e07a6a"]

CONSULTA = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount
                              totalPullRequestContributions totalIssueContributions }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes { stargazerCount
              languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                edges { size node { name } } } }
    }
  }
}"""


def consultar():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        datos = json.load(r)
    if "errors" in datos:
        raise SystemExit(datos["errors"])
    return datos["data"]["user"]


def marco(ancho, alto, titulo, cuerpo):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}">
  <style>
    .t {{ font: 600 17px 'Segoe UI', Ubuntu, sans-serif; fill: {C["acento"]}; }}
    .e {{ font: 400 14px 'Segoe UI', Ubuntu, sans-serif; fill: {C["suave"]}; }}
    .v {{ font: 700 14px 'Segoe UI', Ubuntu, sans-serif; fill: {C["texto"]}; }}
  </style>
  <rect x="0.5" y="0.5" rx="10" width="{ancho - 1}" height="{alto - 1}" fill="{C["fondo"]}" stroke="{C["borde"]}"/>
  <text x="25" y="35" class="t">{escape(titulo)}</text>
{cuerpo}
</svg>
'''


def tarjeta_estadisticas(u):
    cc = u["contributionsCollection"]
    filas = [
        ("★", "Estrellas totales", sum(r["stargazerCount"] for r in u["repositories"]["nodes"])),
        ("✎", "Commits (este año)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("⇄", "Pull requests", cc["totalPullRequestContributions"]),
        ("!", "Issues", cc["totalIssueContributions"]),
        ("▣", "Repositorios", u["repositories"]["totalCount"]),
        ("♥", "Seguidores", u["followers"]["totalCount"]),
    ]
    cuerpo = "".join(
        f'  <text x="25" y="{70 + i * 25}" fill="{C["icono"]}" style="font: 14px sans-serif">{icono}</text>\n'
        f'  <text x="50" y="{70 + i * 25}" class="e">{escape(nombre)}:</text>\n'
        f'  <text x="300" y="{70 + i * 25}" class="v" text-anchor="end">{valor}</text>\n'
        for i, (icono, nombre, valor) in enumerate(filas))
    return marco(330, 225, f"Estadísticas de {u['name'] or USUARIO}", cuerpo)


def tarjeta_lenguajes(u):
    total = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            total[e["node"]["name"]] = total.get(e["node"]["name"], 0) + e["size"]
    top = sorted(total.items(), key=lambda x: -x[1])[:6]
    suma = sum(v for _, v in top) or 1
    cuerpo = ""
    # Una fila por lenguaje: nombre, barra proporcional y porcentaje
    for i, (nombre, v) in enumerate(top):
        y, color, pct = 70 + i * 25, COLORES_LENGUAJES[i], 100 * v / suma
        cuerpo += (f'  <text x="25" y="{y}" class="e">{escape(nombre)}</text>\n'
                   f'  <rect x="125" y="{y - 9}" width="120" height="8" rx="4" fill="{C["barra"]}"/>\n'
                   f'  <rect x="125" y="{y - 9}" width="{max(8, 1.2 * pct):.1f}" height="8" rx="4" fill="{color}"/>\n'
                   f'  <text x="305" y="{y}" class="v" text-anchor="end">{pct:.1f}%</text>\n')
    if not top:
        cuerpo += '  <text x="25" y="90" class="e">Aún no hay código en tus repositorios.</text>\n'
    return marco(330, 225, "Lenguajes más usados", cuerpo)


if __name__ == "__main__":
    u = consultar()
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, svg in (("estadisticas.svg", tarjeta_estadisticas(u)), ("lenguajes.svg", tarjeta_lenguajes(u))):
        with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as f:
            f.write(svg)
    print("Tarjetas actualizadas en", os.path.normpath(SALIDA))
