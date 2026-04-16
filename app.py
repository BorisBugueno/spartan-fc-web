"""
Spartan FC - Plataforma de Estadísticas
========================================
App en Streamlit que lee `data/Resultados.xlsx` y genera automáticamente:
 - Tabla de posiciones (PJ, PG, PE, PP, GF, GC, DIF, Pts) ordenada por puntaje
 - Fixture agrupado por fecha
 - Goleadores y Asistencias de jugadores de Spartan
Separa los cálculos para Serie 35 y Serie 45.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuración general de la página
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).parent
EXCEL_PATH = ROOT / "data" / "Resultados.xlsx"
LOGO_PATH = ROOT / "assets" / "Logo_Oficial.jpeg"

st.set_page_config(
    page_title="Spartan FC · Estadísticas",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "⚽",
    layout="centered",          # mobile-first
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------- #
# Estilos (identidad Spartan: negro, dorado, rojo, blanco)
# --------------------------------------------------------------------------- #

CUSTOM_CSS = """
<style>
  :root {
      --spartan-black: #0b0b0b;
      --spartan-gold:  #f5c518;
      --spartan-red:   #e63946;
      --spartan-white: #ffffff;
      --spartan-grey:  #1e1e1e;
  }

  /* Fondo general */
  .stApp {
      background: radial-gradient(ellipse at top, #161616 0%, var(--spartan-black) 70%);
      color: var(--spartan-white);
  }

  /* Títulos en dorado */
  h1, h2, h3, h4 { color: var(--spartan-gold) !important; font-weight: 800; }

  /* Hero */
  .hero {
      text-align: center;
      padding: 0.5rem 0 1.25rem 0;
      border-bottom: 2px solid var(--spartan-gold);
      margin-bottom: 1.25rem;
  }
  .hero h1 {
      font-size: 2rem;
      letter-spacing: 0.12em;
      margin: 0.5rem 0 0.25rem 0;
      text-transform: uppercase;
  }
  .hero p { color: #c9c9c9; margin: 0; font-size: 0.9rem; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
      gap: 4px;
      background: var(--spartan-grey);
      padding: 4px;
      border-radius: 10px;
      border: 1px solid #333;
  }
  .stTabs [data-baseweb="tab"] {
      color: #c9c9c9;
      background: transparent;
      border-radius: 8px;
      padding: 8px 14px;
      font-weight: 600;
  }
  .stTabs [aria-selected="true"] {
      background: var(--spartan-gold) !important;
      color: var(--spartan-black) !important;
  }

  /* Tablas */
  .stDataFrame, .stTable {
      border: 1px solid #333;
      border-radius: 10px;
      overflow: hidden;
  }

  /* Tarjetas de partido */
  .match-card {
      background: var(--spartan-grey);
      border: 1px solid #2a2a2a;
      border-left: 4px solid var(--spartan-gold);
      border-radius: 10px;
      padding: 10px 14px;
      margin-bottom: 8px;
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 10px;
      align-items: center;
      font-size: 0.95rem;
  }
  .match-card.spartan { border-left-color: var(--spartan-red); }
  .match-card .team-local   { text-align: right; }
  .match-card .team-visita  { text-align: left; }
  .match-card .score {
      background: var(--spartan-black);
      color: var(--spartan-gold);
      border: 1px solid var(--spartan-gold);
      border-radius: 6px;
      padding: 2px 10px;
      font-weight: 800;
      min-width: 60px;
      text-align: center;
  }
  .match-card .score.pending { color: #777; border-color: #444; }
  .spartan-name { color: var(--spartan-red); font-weight: 700; }

  /* Chip de fecha */
  .fecha-chip {
      display: inline-block;
      background: var(--spartan-gold);
      color: var(--spartan-black);
      padding: 4px 12px;
      border-radius: 999px;
      font-weight: 800;
      font-size: 0.85rem;
      margin: 14px 0 8px 0;
      letter-spacing: 0.05em;
  }

  /* KPI cards */
  .kpi {
      background: var(--spartan-grey);
      border: 1px solid #2a2a2a;
      border-radius: 10px;
      padding: 12px;
      text-align: center;
  }
  .kpi .label { color: #aaa; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; }
  .kpi .value { color: var(--spartan-gold); font-size: 1.6rem; font-weight: 800; }

  /* Responsive para celulares */
  @media (max-width: 480px) {
      .hero h1 { font-size: 1.4rem; }
      .match-card { font-size: 0.85rem; padding: 8px 10px; }
  }

  /* Ocultar el footer de Streamlit */
  footer, #MainMenu { visibility: hidden; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Lectura y parsing del Excel
# --------------------------------------------------------------------------- #

SPARTAN_NAME = "Spartan F.C."

EXPECTED_COLS = [
    "Fecha", "Local", "Goles L", "vs", "Goles V", "Visita",
    "Goles Spartan", "Asistencia Spartan",
]


def _clean(value) -> str:
    """Normaliza strings: quita espacios extra. None -> ''."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_players(cell: str) -> list[str]:
    """
    'Sady, Pita; Juan'  ->  ['Sady', 'Pita', 'Juan']
    Un nombre repetido cuenta como múltiples goles/asistencias (ej: 'Sady, Sady').
    """
    if not cell:
        return []
    # Acepta coma, punto y coma o salto de línea como separadores
    raw = cell.replace(";", ",").replace("\n", ",")
    return [p.strip() for p in raw.split(",") if p.strip()]


@st.cache_data(ttl=60, show_spinner=False)
def load_data(path: Path) -> dict[str, pd.DataFrame]:
    """Lee todas las hojas del Excel y devuelve un dict {sheet: DataFrame limpio}."""
    sheets = pd.read_excel(path, sheet_name=None)
    cleaned: dict[str, pd.DataFrame] = {}
    for name, df in sheets.items():
        # Validar columnas esperadas
        missing = [c for c in EXPECTED_COLS if c not in df.columns]
        if missing:
            st.warning(f"Hoja '{name}' le faltan columnas: {missing}")
            continue

        df = df.copy()
        # Quitar filas separadoras '---'
        df = df[df["Local"].astype(str).str.strip() != "---"]
        # Limpiar strings
        for col in ["Fecha", "Local", "Visita", "Goles Spartan", "Asistencia Spartan"]:
            df[col] = df[col].map(_clean)
        cleaned[name] = df.reset_index(drop=True)
    return cleaned


# --------------------------------------------------------------------------- #
# Cálculos
# --------------------------------------------------------------------------- #

def compute_standings(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve la tabla de posiciones ordenada: Pts → DIF → GF."""
    stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0}
    )

    for _, row in df.iterrows():
        local = row["Local"]
        visita = row["Visita"]
        gl, gv = row["Goles L"], row["Goles V"]

        # Saltar partidos no jugados o fechas libres
        if pd.isna(gl) or pd.isna(gv):
            continue
        if local.upper() == "LIBRE" or visita.upper() == "LIBRE":
            continue
        if not local or not visita:
            continue

        gl, gv = int(gl), int(gv)
        for team in (local, visita):
            stats[team]["PJ"] += 1

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
        dif = s["GF"] - s["GC"]
        rows.append(
            {"Equipo": team, "PJ": s["PJ"], "PG": s["PG"], "PE": s["PE"],
             "PP": s["PP"], "GF": s["GF"], "GC": s["GC"], "DIF": dif, "Pts": pts}
        )

    if not rows:
        return pd.DataFrame(
            columns=["Pos", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DIF", "Pts"]
        )

    tabla = pd.DataFrame(rows).sort_values(
        by=["Pts", "DIF", "GF"], ascending=[False, False, False]
    ).reset_index(drop=True)
    tabla.insert(0, "Pos", tabla.index + 1)
    return tabla


def compute_individual_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula goleadores y asistencias de Spartan."""
    goles: dict[str, int] = defaultdict(int)
    asists: dict[str, int] = defaultdict(int)

    for _, row in df.iterrows():
        for p in _parse_players(row["Goles Spartan"]):
            goles[p] += 1
        for p in _parse_players(row["Asistencia Spartan"]):
            asists[p] += 1

    goleadores = (
        pd.DataFrame(goles.items(), columns=["Jugador", "Goles"])
        .sort_values("Goles", ascending=False)
        .reset_index(drop=True)
    )
    asistencias = (
        pd.DataFrame(asists.items(), columns=["Jugador", "Asistencias"])
        .sort_values("Asistencias", ascending=False)
        .reset_index(drop=True)
    )
    if not goleadores.empty:
        goleadores.insert(0, "#", goleadores.index + 1)
    if not asistencias.empty:
        asistencias.insert(0, "#", asistencias.index + 1)
    return goleadores, asistencias


# --------------------------------------------------------------------------- #
# Render helpers
# --------------------------------------------------------------------------- #

def _fmt_score(g):
    """Formato seguro de un gol: None -> '-', 3.0 -> '3'."""
    if pd.isna(g):
        return "-"
    try:
        return str(int(g))
    except (ValueError, TypeError):
        return str(g)


def render_fixture(df: pd.DataFrame) -> None:
    """Renderiza el fixture agrupado por fecha, con tarjetas por partido."""
    if df.empty:
        st.info("Sin partidos cargados.")
        return

    for fecha, grupo in df.groupby("Fecha", sort=False):
        st.markdown(f'<span class="fecha-chip">{fecha}</span>', unsafe_allow_html=True)
        for _, row in grupo.iterrows():
            local, visita = row["Local"], row["Visita"]
            gl = _fmt_score(row["Goles L"])
            gv = _fmt_score(row["Goles V"])

            is_spartan = SPARTAN_NAME in local or SPARTAN_NAME in visita
            played = gl != "-" and gv != "-"
            card_class = "match-card spartan" if is_spartan else "match-card"
            score_class = "score" if played else "score pending"

            # Marcar visualmente a Spartan con color rojo
            def highlight(name: str) -> str:
                return (f'<span class="spartan-name">{name}</span>'
                        if SPARTAN_NAME in name else name)

            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="team-local">{highlight(local)}</div>
                    <div class="{score_class}">{gl} · {gv}</div>
                    <div class="team-visita">{highlight(visita)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_standings(tabla: pd.DataFrame) -> None:
    if tabla.empty:
        st.info("Aún no hay partidos jugados en esta categoría.")
        return
    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pos": st.column_config.NumberColumn("#", width="small"),
            "Equipo": st.column_config.TextColumn("Equipo", width="medium"),
            "Pts": st.column_config.NumberColumn("Pts", help="Puntos (PG×3 + PE)"),
            "DIF": st.column_config.NumberColumn("DIF", help="Diferencia de goles"),
        },
    )


def render_individuals(goleadores: pd.DataFrame, asistencias: pd.DataFrame) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🥅 Goleadores")
        if goleadores.empty:
            st.caption("Sin goles registrados aún.")
        else:
            st.dataframe(goleadores, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("#### 🎯 Asistencias")
        if asistencias.empty:
            st.caption("Sin asistencias registradas aún.")
        else:
            st.dataframe(asistencias, use_container_width=True, hide_index=True)


def render_kpis(tabla: pd.DataFrame, df: pd.DataFrame) -> None:
    """Tarjetas resumen para Spartan: Pts, PJ, ranking, GF, GC."""
    spartan_row = tabla[tabla["Equipo"].str.contains(SPARTAN_NAME, na=False)]
    if spartan_row.empty:
        return
    s = spartan_row.iloc[0]

    cols = st.columns(5)
    kpis = [
        ("Posición", f"{int(s['Pos'])}°"),
        ("Puntos",   int(s["Pts"])),
        ("PJ",       int(s["PJ"])),
        ("GF",       int(s["GF"])),
        ("GC",       int(s["GC"])),
    ]
    for col, (label, value) in zip(cols, kpis):
        col.markdown(
            f'<div class="kpi"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# App principal
# --------------------------------------------------------------------------- #

def render_category(df: pd.DataFrame) -> None:
    tabla = compute_standings(df)
    goleadores, asistencias = compute_individual_stats(df)

    render_kpis(tabla, df)
    st.markdown("")
    sub_tabs = st.tabs(["📊 Posiciones", "📅 Fixture", "⭐ Individuales"])
    with sub_tabs[0]:
        render_standings(tabla)
    with sub_tabs[1]:
        render_fixture(df)
    with sub_tabs[2]:
        render_individuals(goleadores, asistencias)


def main() -> None:
    # Hero / cabecera
    col_logo, col_text = st.columns([1, 3], vertical_alignment="center")
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=110)
    with col_text:
        st.markdown(
            '<div class="hero">'
            '<h1>Spartan FC</h1>'
            '<p>Estadísticas oficiales · Temporada 2026</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    if not EXCEL_PATH.exists():
        st.error(f"No se encontró el Excel en: {EXCEL_PATH}")
        st.stop()

    data = load_data(EXCEL_PATH)
    if not data:
        st.error("El Excel no tiene hojas válidas.")
        st.stop()

    # Ordenar: Serie 35 primero, luego Serie 45, luego el resto
    order = sorted(data.keys(), key=lambda n: (0 if "35" in n else 1 if "45" in n else 2, n))
    tabs = st.tabs([f"🏆 {name}" for name in order])
    for tab, name in zip(tabs, order):
        with tab:
            render_category(data[name])

    # Footer
    st.markdown(
        '<div style="text-align:center;margin-top:2rem;padding-top:1rem;'
        'border-top:1px solid #2a2a2a;color:#666;font-size:0.8rem;">'
        'Spartan FC · Actualizado automáticamente desde el fixture oficial'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
