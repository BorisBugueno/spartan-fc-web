"""
Spartan FC - Plataforma de Estadísticas v2
==========================================
Funcionalidades:
 - Tabla de posiciones con Spartan destacado en dorado
 - Fixture por fecha con tarjetas
 - Goleadores y asistencias ordenados de mayor a menor
 - Próximos partidos de Spartan
 - Evolución de puntos por fecha (gráfico interactivo)
 - Racha actual de resultados (últimos 5)
 - Banner especial si Spartan es líder
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).parent
EXCEL_PATH = ROOT / "data" / "Resultados.xlsx"
LOGO_PATH  = ROOT / "assets" / "Logo_Oficial.jpeg"
SPARTAN_NAME = "Spartan F.C."

st.set_page_config(
    page_title="Spartan FC · Estadísticas",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "⚽",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #

CUSTOM_CSS = """
<style>
  :root {
    --gold:  #f5c518;
    --red:   #e63946;
    --black: #0b0b0b;
    --grey:  #1e1e1e;
    --white: #ffffff;
  }

  .stApp {
    background: radial-gradient(ellipse at top, #161616 0%, var(--black) 70%);
    color: var(--white);
  }

  h1,h2,h3,h4 { color: var(--gold) !important; font-weight: 800; }

  /* Hero */
  .hero { text-align:center; padding:.5rem 0 1.25rem; border-bottom:2px solid var(--gold); margin-bottom:1.25rem; }
  .hero h1 { font-size:2rem; letter-spacing:.12em; margin:.5rem 0 .25rem; text-transform:uppercase; }
  .hero p  { color:#c9c9c9; margin:0; font-size:.9rem; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { gap:4px; background:var(--grey); padding:4px; border-radius:10px; border:1px solid #333; }
  .stTabs [data-baseweb="tab"]      { color:#c9c9c9; background:transparent; border-radius:8px; padding:8px 14px; font-weight:600; }
  .stTabs [aria-selected="true"]    { background:var(--gold) !important; color:var(--black) !important; }

  /* Banner lider */
  .leader-banner {
    background: linear-gradient(135deg, #1a1000 0%, #2e1f00 100%);
    border: 2px solid var(--gold);
    border-radius: 14px;
    padding: 14px 18px;
    text-align: center;
    margin-bottom: 1rem;
    animation: pulse-border 2s infinite;
  }
  @keyframes pulse-border {
    0%,100% { box-shadow: 0 0 8px #f5c51860; }
    50%      { box-shadow: 0 0 22px #f5c518aa; }
  }
  .leader-banner .trophy { font-size:2rem; }
  .leader-banner p { margin:.3rem 0 0; color:var(--gold); font-weight:700; font-size:1rem; }

  /* KPIs */
  .kpi { background:var(--grey); border:1px solid #2a2a2a; border-radius:10px; padding:12px; text-align:center; }
  .kpi .label { color:#aaa; font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; }
  .kpi .value { color:var(--gold); font-size:1.5rem; font-weight:800; }

  /* Racha */
  .racha { display:flex; gap:6px; align-items:center; margin:6px 0 12px; }
  .racha-badge { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:.85rem; }
  .racha-badge.G { background:#1a5c1a; color:#4ade80; border:1px solid #4ade80; }
  .racha-badge.E { background:#2a2a00; color:var(--gold); border:1px solid var(--gold); }
  .racha-badge.P { background:#5c1a1a; color:#f87171; border:1px solid #f87171; }
  .racha-label   { color:#aaa; font-size:.8rem; margin-left:4px; }

  /* Tabla posiciones */
  .standings-table { width:100%; border-collapse:collapse; font-size:.88rem; border-radius:10px; overflow:hidden; }
  .standings-table th {
    background:#2a2a2a; color:var(--gold); padding:8px 6px; text-align:center;
    font-size:.75rem; letter-spacing:.08em; text-transform:uppercase;
  }
  .standings-table th:nth-child(2) { text-align:left; }
  .standings-table td { padding:7px 6px; text-align:center; border-bottom:1px solid #222; }
  .standings-table td:nth-child(2) { text-align:left; font-weight:600; }
  .standings-table tr:last-child td { border-bottom:none; }
  .standings-table tr:hover td { background:#1a1a1a; }

  /* Fila Spartan destacada */
  .row-spartan td {
    background: linear-gradient(90deg, #1a0e00 0%, #110900 100%) !important;
    color: var(--gold) !important;
    font-weight: 800 !important;
    border-top: 1px solid #3a2800 !important;
    border-bottom: 1px solid #3a2800 !important;
  }

  /* Tarjetas partido */
  .match-card {
    background:var(--grey); border:1px solid #2a2a2a; border-left:4px solid var(--gold);
    border-radius:10px; padding:10px 14px; margin-bottom:8px;
    display:grid; grid-template-columns:1fr auto 1fr; gap:10px; align-items:center; font-size:.95rem;
  }
  .match-card.spartan { border-left-color:var(--red); }
  .match-card.proximo { border-left-color:#5566ff; }
  .team-local  { text-align:right; }
  .team-visita { text-align:left; }
  .score {
    background:var(--black); color:var(--gold); border:1px solid var(--gold);
    border-radius:6px; padding:2px 10px; font-weight:800; min-width:60px; text-align:center;
  }
  .score.pending { color:#555; border-color:#333; }
  .spartan-name  { color:var(--red); font-weight:700; }

  /* Chips */
  .fecha-chip { display:inline-block; background:var(--gold); color:var(--black); padding:4px 12px; border-radius:999px; font-weight:800; font-size:.82rem; margin:14px 0 8px; letter-spacing:.05em; }
  .section-title { color:var(--gold); font-weight:800; font-size:1rem; margin:12px 0 6px; }

  /* Tabla goleadores */
  .scorer-table { width:100%; border-collapse:collapse; font-size:.88rem; }
  .scorer-table th { background:#2a2a2a; color:var(--gold); padding:7px 8px; text-align:left; font-size:.75rem; text-transform:uppercase; }
  .scorer-table td { padding:7px 8px; border-bottom:1px solid #222; }
  .scorer-table tr:last-child td { border-bottom:none; }

  /* Proximos */
  .proximos-header { color:#8888ff; font-weight:700; font-size:.85rem; margin-bottom:6px; text-transform:uppercase; letter-spacing:.1em; }

  footer, #MainMenu { visibility:hidden; }

  @media (max-width:480px) {
    .hero h1    { font-size:1.4rem; }
    .match-card { font-size:.82rem; padding:8px 10px; }
    .kpi .value { font-size:1.2rem; }
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Lectura de datos
# --------------------------------------------------------------------------- #

def _clean(v) -> str:
    return "" if pd.isna(v) else str(v).strip()

def _parse_players(cell: str) -> list[str]:
    if not cell:
        return []
    return [p.strip() for p in cell.replace(";", ",").replace("\n", ",").split(",") if p.strip()]

def _fecha_num(f: str) -> int:
    import re
    m = re.search(r"\d+", f)
    return int(m.group()) if m else 0


@st.cache_data(ttl=60, show_spinner=False)
def load_data(path: Path) -> dict[str, pd.DataFrame]:
    sheets = pd.read_excel(path, sheet_name=None)
    out = {}
    for name, df in sheets.items():
        df = df.copy()
        df = df[df["Local"].astype(str).str.strip() != "---"]
        for col in ["Fecha", "Local", "Visita", "Goles Spartan", "Asistencia Spartan"]:
            if col in df.columns:
                df[col] = df[col].map(_clean)
        out[name] = df.reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
# Cálculos
# --------------------------------------------------------------------------- #

def compute_standings(df: pd.DataFrame) -> pd.DataFrame:
    stats: dict[str, dict] = defaultdict(
        lambda: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0}
    )
    for _, row in df.iterrows():
        local, visita = row["Local"], row["Visita"]
        gl, gv = row["Goles L"], row["Goles V"]
        if pd.isna(gl) or pd.isna(gv):
            continue
        if "LIBRE" in local.upper() or "LIBRE" in visita.upper():
            continue
        if not local or not visita:
            continue
        gl, gv = int(gl), int(gv)
        for t in (local, visita):
            stats[t]["PJ"] += 1
        stats[local]["GF"] += gl
        stats[local]["GC"] += gv
        stats[visita]["GF"] += gv
        stats[visita]["GC"] += gl
        if gl > gv:
            stats[local]["PG"] += 1
            stats[visita]["PP"] += 1
        elif gl < gv:
            stats[visita]["PG"] += 1
            stats[local]["PP"] += 1
        else:
            stats[local]["PE"] += 1
            stats[visita]["PE"] += 1

    rows = []
    for team, s in stats.items():
        pts = s["PG"] * 3 + s["PE"]
        rows.append({
            "Equipo": team, "PJ": s["PJ"], "PG": s["PG"], "PE": s["PE"],
            "PP": s["PP"], "GF": s["GF"], "GC": s["GC"],
            "DIF": s["GF"] - s["GC"], "Pts": pts,
        })

    if not rows:
        return pd.DataFrame(columns=["Pos", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DIF", "Pts"])

    tabla = (
        pd.DataFrame(rows)
        .sort_values(["Pts", "DIF", "GF"], ascending=[False, False, False])
        .reset_index(drop=True)
    )
    tabla.insert(0, "Pos", tabla.index + 1)
    return tabla


def compute_individual_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    goles: dict[str, int] = defaultdict(int)
    asists: dict[str, int] = defaultdict(int)
    for _, row in df.iterrows():
        for p in _parse_players(row["Goles Spartan"]):
            goles[p] += 1
        for p in _parse_players(row["Asistencia Spartan"]):
            asists[p] += 1

    def make_df(d, col):
        df_out = (
            pd.DataFrame(d.items(), columns=["Jugador", col])
            .sort_values(col, ascending=False)
            .reset_index(drop=True)
        )
        if not df_out.empty:
            df_out.insert(0, "#", df_out.index + 1)
        return df_out

    return make_df(goles, "Goles"), make_df(asists, "Asistencias")


def get_spartan_matches(df: pd.DataFrame):
    mask = (
        df["Local"].str.contains(SPARTAN_NAME, na=False) |
        df["Visita"].str.contains(SPARTAN_NAME, na=False)
    )
    spartan = df[mask].copy()
    spartan["_fn"] = spartan["Fecha"].map(_fecha_num)
    spartan = spartan.sort_values("_fn")

    played, upcoming = [], []
    for _, row in spartan.iterrows():
        is_local = SPARTAN_NAME in row["Local"]
        rival = row["Visita"] if is_local else row["Local"]
        if pd.notna(row["Goles L"]) and pd.notna(row["Goles V"]):
            gf = int(row["Goles L"]) if is_local else int(row["Goles V"])
            gc = int(row["Goles V"]) if is_local else int(row["Goles L"])
            res = "G" if gf > gc else ("E" if gf == gc else "P")
            played.append({
                "Fecha": row["Fecha"].strip(), "Rival": rival.strip(),
                "Local": is_local, "GF": gf, "GC": gc, "Res": res,
            })
        else:
            upcoming.append({
                "Fecha": row["Fecha"].strip(), "Rival": rival.strip(),
                "EsLocal": is_local,
            })
    return played, upcoming


def compute_evolution(played: list[dict]) -> tuple[list[str], list[int]]:
    fechas, pts_acum = [], []
    acc = 0
    for m in played:
        acc += 3 if m["Res"] == "G" else (1 if m["Res"] == "E" else 0)
        fechas.append(m["Fecha"])
        pts_acum.append(acc)
    return fechas, pts_acum


# --------------------------------------------------------------------------- #
# Render helpers
# --------------------------------------------------------------------------- #

def _fmt(g) -> str:
    if pd.isna(g):
        return "-"
    try:
        return str(int(g))
    except Exception:
        return str(g)

def _hl(name: str) -> str:
    return f'<span class="spartan-name">{name}</span>' if SPARTAN_NAME in name else name


def render_leader_banner():
    st.markdown(
        '<div class="leader-banner">'
        '<div class="trophy">🏆</div>'
        '<p>¡SPARTAN FC ES LÍDER DE LA TABLA!</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_kpis(tabla: pd.DataFrame, played: list[dict]):
    row = tabla[tabla["Equipo"].str.contains(SPARTAN_NAME, na=False)]
    if row.empty:
        return
    s = row.iloc[0]

    # Racha últimos 5 partidos
    racha = played[-5:]
    racha_html = '<div class="racha">'
    for m in racha:
        racha_html += f'<div class="racha-badge {m["Res"]}">{m["Res"]}</div>'
    if not racha:
        racha_html += '<span class="racha-label">Sin partidos aún</span>'
    else:
        racha_html += '<span class="racha-label">Últimos resultados</span>'
    racha_html += "</div>"
    st.markdown(racha_html, unsafe_allow_html=True)

    cols = st.columns(5)
    kpis = [
        ("Posición", f"{int(s['Pos'])}°"),
        ("Puntos", int(s["Pts"])),
        ("PJ", int(s["PJ"])),
        ("GF", int(s["GF"])),
        ("GC", int(s["GC"])),
    ]
    for col, (label, value) in zip(cols, kpis):
        col.markdown(
            f'<div class="kpi"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>',
            unsafe_allow_html=True,
        )


def render_standings(tabla: pd.DataFrame):
    if tabla.empty:
        st.info("Sin partidos jugados aún.")
        return

    medal = {1: "🥇", 2: "🥈", 3: "🥉"}
    html = '<table class="standings-table"><thead><tr>'
    for col in ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DIF", "Pts"]:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    for _, row in tabla.iterrows():
        is_spartan = SPARTAN_NAME in row["Equipo"]
        tr_class = "row-spartan" if is_spartan else ""
        pos = int(row["Pos"])
        pos_str = medal.get(pos, str(pos))
        dif_val = int(row["DIF"])
        dif_str = f"+{dif_val}" if dif_val > 0 else str(dif_val)
        html += f'<tr class="{tr_class}">'
        html += f"<td>{pos_str}</td>"
        # Agregar ícono de espada a Spartan
        equipo_str = f"⚔️ {row['Equipo']}" if is_spartan else row["Equipo"]
        html += f"<td>{equipo_str}</td>"
        for col in ["PJ", "PG", "PE", "PP", "GF", "GC"]:
            html += f"<td>{int(row[col])}</td>"
        html += f"<td>{dif_str}</td>"
        html += f"<td><b>{int(row['Pts'])}</b></td>"
        html += "</tr>"

    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


def render_fixture(df: pd.DataFrame):
    if df.empty:
        st.info("Sin partidos cargados.")
        return
    for fecha, grupo in df.groupby("Fecha", sort=False):
        st.markdown(f'<span class="fecha-chip">{fecha}</span>', unsafe_allow_html=True)
        for _, row in grupo.iterrows():
            local, visita = row["Local"], row["Visita"]
            gl, gv = _fmt(row["Goles L"]), _fmt(row["Goles V"])
            is_spartan = SPARTAN_NAME in local or SPARTAN_NAME in visita
            played = gl != "-" and gv != "-"
            card_cls   = "match-card spartan" if is_spartan else "match-card"
            score_cls  = "score" if played else "score pending"
            st.markdown(
                f'<div class="{card_cls}">'
                f'<div class="team-local">{_hl(local)}</div>'
                f'<div class="{score_cls}">{gl} · {gv}</div>'
                f'<div class="team-visita">{_hl(visita)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_upcoming(upcoming: list[dict]):
    if not upcoming:
        st.info("No hay próximos partidos registrados.")
        return
    st.markdown('<div class="proximos-header">🔜 Próximos compromisos de Spartan</div>', unsafe_allow_html=True)
    for m in upcoming[:6]:
        local_name  = SPARTAN_NAME if m["EsLocal"] else m["Rival"]
        visita_name = m["Rival"] if m["EsLocal"] else SPARTAN_NAME
        condicion   = "🏠 Local" if m["EsLocal"] else "✈️ Visita"
        st.markdown(
            f'<div class="match-card proximo">'
            f'<div class="team-local">{_hl(local_name)}</div>'
            f'<div class="score pending">vs</div>'
            f'<div class="team-visita">{_hl(visita_name)}</div>'
            f'</div>'
            f'<div style="text-align:center;margin:-4px 0 8px;font-size:.75rem;color:#666;">'
            f'{m["Fecha"]} · {condicion}</div>',
            unsafe_allow_html=True,
        )


def render_individuals(goleadores: pd.DataFrame, asistencias: pd.DataFrame):
    medals = ["🥇", "🥈", "🥉"]

    def scorer_table(df_in: pd.DataFrame, col: str):
        if df_in.empty:
            st.caption(f"Sin {col.lower()} registradas aún.")
            return
        rows_html = ""
        for _, row in df_in.iterrows():
            pos = int(row["#"]) - 1
            medal_str = medals[pos] if pos < 3 else f'{int(row["#"])}.'
            rows_html += (
                f"<tr>"
                f"<td>{medal_str}</td>"
                f"<td>{row['Jugador']}</td>"
                f"<td style='text-align:center;color:#f5c518;font-weight:800;'>{int(row[col])}</td>"
                f"</tr>"
            )
        html = (
            f'<table class="scorer-table"><thead><tr>'
            f'<th>#</th><th>Jugador</th><th style="text-align:center;">{col}</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table>'
        )
        st.markdown(html, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🥅 Goleadores")
        scorer_table(goleadores, "Goles")
    with col2:
        st.markdown("#### 🎯 Asistencias")
        scorer_table(asistencias, "Asistencias")


def render_evolution(played: list[dict], categoria: str):
    if len(played) < 1:
        st.info("Se necesitan al menos 2 fechas jugadas para mostrar la evolución.")
        return

    fechas, pts = compute_evolution(played)
    f_plot = ["Inicio"] + fechas
    p_plot = [0] + pts
    colores = [
        "#4ade80" if m["Res"] == "G" else ("#f5c518" if m["Res"] == "E" else "#f87171")
        for m in played
    ]

    fig = go.Figure()

    # Área bajo la curva
    fig.add_trace(go.Scatter(
        x=f_plot, y=p_plot,
        fill="tozeroy", fillcolor="rgba(245,197,24,0.07)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))

    # Línea principal
    fig.add_trace(go.Scatter(
        x=f_plot, y=p_plot,
        mode="lines+markers+text",
        line=dict(color="#f5c518", width=3),
        marker=dict(size=13, color=["#444"] + colores, line=dict(color="#0b0b0b", width=2)),
        text=[""] + [str(p) for p in pts],
        textposition="top center",
        textfont=dict(color="#f5c518", size=13),
        hovertemplate="<b>%{x}</b><br>Pts acumulados: %{y}<extra></extra>",
        name="Puntos",
    ))

    fig.update_layout(
        title=dict(
            text=f"📈 Evolución de Puntos — {categoria}",
            font=dict(color="#f5c518", size=14), x=0.5,
        ),
        paper_bgcolor="#0b0b0b", plot_bgcolor="#0b0b0b",
        font=dict(color="#cccccc"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#1e1e1e", tickfont=dict(size=11), dtick=1, rangemode="tozero"),
        margin=dict(l=20, r=20, t=50, b=30),
        height=300,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Leyenda de colores
    st.markdown(
        '<div style="display:flex;gap:16px;justify-content:center;margin-bottom:12px;font-size:.78rem;">'
        '<span>🟢 Victoria</span><span>🟡 Empate</span><span>🔴 Derrota</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Detalle de cada partido
    st.markdown('<div class="section-title">Detalle de partidos jugados</div>', unsafe_allow_html=True)
    for m in played:
        color = "#4ade80" if m["Res"] == "G" else ("#f5c518" if m["Res"] == "E" else "#f87171")
        label = "Victoria" if m["Res"] == "G" else ("Empate" if m["Res"] == "E" else "Derrota")
        cond  = "🏠" if m["Local"] else "✈️"
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 12px;background:#1e1e1e;border-radius:8px;margin-bottom:5px;'
            f'border-left:3px solid {color};">'
            f'<span style="font-size:.85rem;">{cond} {m["Fecha"]} · vs {m["Rival"]}</span>'
            f'<span style="font-weight:800;color:{color};font-size:.9rem;">'
            f'{m["GF"]}–{m["GC"]} <span style="font-size:.72rem;opacity:.8;">({label})</span></span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# App principal
# --------------------------------------------------------------------------- #

def render_category(df: pd.DataFrame, name: str):
    tabla = compute_standings(df)
    gol, asist = compute_individual_stats(df)
    played, upcoming = get_spartan_matches(df)

    # Banner si Spartan es líder
    spartan_row = tabla[tabla["Equipo"].str.contains(SPARTAN_NAME, na=False)]
    if not spartan_row.empty and int(spartan_row.iloc[0]["Pos"]) == 1:
        render_leader_banner()

    render_kpis(tabla, played)
    st.markdown("")

    tabs = st.tabs(["📊 Posiciones", "📅 Fixture", "⭐ Individuales", "📈 Evolución", "🔜 Próximos"])

    with tabs[0]:
        render_standings(tabla)
    with tabs[1]:
        render_fixture(df)
    with tabs[2]:
        render_individuals(gol, asist)
    with tabs[3]:
        render_evolution(played, name)
    with tabs[4]:
        render_upcoming(upcoming)


def main():
    col_logo, col_text = st.columns([1, 3], vertical_alignment="center")
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=110)
    with col_text:
        st.markdown(
            '<div class="hero"><h1>Spartan FC</h1>'
            '<p>Estadísticas oficiales · Temporada 2026</p></div>',
            unsafe_allow_html=True,
        )

    if not EXCEL_PATH.exists():
        st.error(f"No se encontró el Excel en: {EXCEL_PATH}")
        st.stop()

    data = load_data(EXCEL_PATH)
    if not data:
        st.error("El Excel no tiene hojas válidas.")
        st.stop()

    order = sorted(data.keys(), key=lambda n: (0 if "35" in n else 1 if "45" in n else 2, n))
    cat_tabs = st.tabs([f"🏆 {n}" for n in order])
    for tab, name in zip(cat_tabs, order):
        with tab:
            render_category(data[name], name)

    st.markdown(
        '<div style="text-align:center;margin-top:2rem;padding-top:1rem;'
        'border-top:1px solid #2a2a2a;color:#555;font-size:.78rem;">'
        'Spartan FC App · Es un producto desarrollado por Boris Bugueño B.'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
