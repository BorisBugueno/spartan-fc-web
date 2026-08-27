"""
Spartan FC - Plataforma de Estadísticas v7
==========================================
CAMBIOS MAYORES:
- Lectura desde Google Sheets (ya no Excel)
- Soporte multi-fase: Regular, Copa de Oro, Copa de Plata
- Serie 45: Grupo A / Grupo B con clasificación cruzada
- Selector de fase dinámico (solo aparece si hay más de una)
- Línea de corte de clasificación en tabla
- Penalizaciones por fase
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).parent
LOGO_PATH = ROOT / "assets" / "Logo_Spartan.png"
LOGO_FALLBACK = ROOT / "assets" / "Logo_Oficial.jpeg"
SPONSOR_MP = ROOT / "assets" / "sponsor_mprental.png"
SPONSOR_INK = ROOT / "assets" / "sponsor_inkubiertos.png"
SPONSOR_BAL = ROOT / "assets" / "sponsor_baldomeros.png"
SPARTAN_NAME = "Spartan F.C."

# Google Sheets
SHEET_ID = "1_lK-mtx_597lNrQ3g-9SjQAw_KBUut9NxcIs9Oulrmw"

# Nombres de pestañas en el Sheet
TABS = {
    "35": {"resultados": "Serie35", "plantel": "Plantel35", "penalizaciones": "Penalizaciones35"},
    "45": {"resultados": "Serie45", "plantel": "Plantel45", "penalizaciones": "Penalizaciones45"},
}

# URLs
INSTAGRAM_URL = "https://www.instagram.com/fc__spartan?igsh=MWtoOTRyaGo2Yjl6aQ=="
MPRENTAL_URL = "https://mprental.cl/"
INKUBIERTOS_URL = "https://www.instagram.com/inkubiertos?igsh=MWFjdmR0dTM4MzA2cQ=="
BALDOMEROS_URL = "https://www.instagram.com/cerveceria_baldomeros?igsh=OHVtZ3cxbGdyYjRi"

# Configuración de clasificación
# Serie 35: 12 equipos, top 6 → Copa de Oro, resto → Copa de Plata
# Serie 45: 2 grupos de 7, top 3 de cada grupo + mejor 4° → Copa de Oro
CLASIFICACION = {
    "35": {"corte_oro": 6, "tipo": "single_group"},
    "45": {"corte_oro_por_grupo": 3, "mejor_cuarto": True, "tipo": "two_groups"},
}

st.set_page_config(
    page_title="Spartan FC · Estadísticas",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "⚽",
    layout="centered",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def _logo_b64(path_str: str) -> str:
    """Embebe imagen como data URI para HTML."""
    import base64
    p = Path(path_str)
    if not p.exists():
        return ""
    media = "image/png" if p.suffix == ".png" else "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{media};base64,{data}"


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
  .hero-v6 {
    display:flex; align-items:center; gap:16px;
    padding:12px 4px 16px;
    border-bottom:1px solid #1f1f1f;
    margin-bottom:16px;
  }
  .hero-logo {
    width:90px; height:90px; flex-shrink:0;
    display:flex; align-items:center; justify-content:center;
    filter: drop-shadow(0 4px 14px rgba(245,197,24,0.32));
  }
  .hero-logo img { width:100%; height:100%; object-fit:contain; }
  .hero-accent {
    width:3px; align-self:stretch; min-height:72px;
    background: linear-gradient(to bottom, #f5c518 0%, #e63946 100%);
    border-radius:2px;
    box-shadow: 0 0 8px rgba(245,197,24,0.3);
  }
  .hero-text { flex:1; min-width:0; }
  .hero-title {
    font-size:1.65rem; font-weight:900; color:#fff;
    letter-spacing:-.015em; line-height:1;
  }
  .hero-title .accent-word { color:var(--gold); }
  .hero-subtitle {
    color:#888; font-size:.8rem; font-weight:500;
    margin-top:6px; display:flex; align-items:center; gap:6px;
  }
  .live-dot {
    width:7px; height:7px; background:#4ade80;
    border-radius:50%; box-shadow:0 0 8px #4ade80;
    animation: live-pulse 2s infinite;
  }
  @keyframes live-pulse {
    0%,100% { opacity:1; box-shadow:0 0 6px #4ade80; }
    50%      { opacity:.65; box-shadow:0 0 12px #4ade80; }
  }

  /* Selector */
  .selector-container {
    padding:0 4px 14px;
    border-bottom:1px solid #1f1f1f;
    margin-bottom:14px;
  }
  .selector-label {
    color:#888;
    font-size:.75rem;
    font-weight:600;
    text-transform:uppercase;
    letter-spacing:.1em;
    margin-bottom:8px;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { gap:4px; background:var(--grey); padding:4px; border-radius:10px; border:1px solid #333; }
  .stTabs [data-baseweb="tab"]      { color:#c9c9c9; background:transparent; border-radius:8px; padding:8px 14px; font-weight:600; }
  .stTabs [aria-selected="true"]    { background:var(--gold) !important; color:var(--black) !important; }

  /* Banner líder */
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
  .kpis {
    display:grid;
    grid-template-columns:repeat(5, 1fr);
    gap:6px;
    margin-bottom:16px;
  }
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
  .standings-table th { background:#2a2a2a; color:var(--gold); padding:8px 6px; text-align:center; font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; }
  .standings-table th:nth-child(2) { text-align:left; }
  .standings-table td { padding:7px 6px; text-align:center; border-bottom:1px solid #222; }
  .standings-table td:nth-child(2) { text-align:left; font-weight:600; }
  .standings-table tr:last-child td { border-bottom:none; }
  .standings-table tr:hover td { background:#1a1a1a; }
  .row-spartan td {
    background: linear-gradient(90deg, #1a0e00 0%, #110900 100%) !important;
    color: var(--gold) !important;
    font-weight: 800 !important;
    border-top: 1px solid #3a2800 !important;
    border-bottom: 1px solid #3a2800 !important;
  }

  /* Marca de penalización */
  .penal-mark { color: #e63946; font-weight: 800; }
  .penal-note {
    margin-top: 10px;
    padding: 10px 14px;
    background: #1a0d0d;
    border-left: 3px solid #e63946;
    border-radius: 8px;
    color: #d99;
    font-size: .78rem;
    line-height: 1.4;
  }

  /* Línea de corte clasificación */
  .cutline-row td {
    border-bottom: 2px dashed #f5c518 !important;
  }
  .cutline-label {
    text-align:center;
    font-size:.7rem;
    font-weight:700;
    padding:4px 0;
    letter-spacing:.05em;
  }
  .cutline-label.oro { color:#f5c518; }
  .cutline-label.plata { color:#aaa; }

  /* Tabla PLANTEL */
  .roster-table { width:100%; border-collapse:collapse; font-size:.88rem; border-radius:10px; overflow:hidden; }
  .roster-table thead { background:#2a2a2a; border-bottom:2px solid var(--gold); }
  .roster-table th { padding:8px 6px; text-align:left; color:var(--gold); font-size:.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; }
  .roster-table th:first-child { width:50px; text-align:center; }
  .roster-table th:last-child { width:60px; text-align:center; }
  .roster-table td { padding:8px 6px; border-bottom:1px solid #1a1a1a; }
  .roster-table tr:last-child td { border-bottom:none; }
  .roster-table tr:hover { background:#161616; }
  .num-badge { display:inline-flex; align-items:center; justify-content:center; min-width:30px; height:30px; background:#2a2a2a; border-radius:6px; font-weight:700; color:var(--gold); font-size:.85rem; }
  .num-badge.sn { background:transparent; border:1px dashed #444; color:#666; font-size:.7rem; }
  .pos-badge { display:inline-block; padding:3px 8px; background:#1a1a1a; border-radius:6px; font-size:.72rem; color:#888; font-weight:600; text-align:center; }
  .role-tag { display:inline-block; padding:3px 8px; border-radius:6px; font-size:.7rem; font-weight:700; margin-left:6px; }
  .role-tag.dt { background:var(--gold); color:var(--black); }
  .role-tag.cap { background:var(--red); color:#fff; }
  .role-tag.ayu { background:#5566ff; color:#fff; }

  /* Cumpleaños */
  .birthday-item { padding:10px 14px; background:#161616; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; border-left:3px solid #f5c518; }
  .birthday-item:last-child { margin-bottom:0; }
  .birthday-name { font-weight:700; color:#fff; font-size:.9rem; }
  .birthday-date { color:#f5c518; font-size:.85rem; font-weight:700; }

  /* Tabla tarjetas rojas */
  .cards-table { width:100%; border-collapse:collapse; font-size:.88rem; }
  .cards-table thead { background:#2a2a2a; border-bottom:2px solid #e63946; }
  .cards-table th { padding:8px 10px; text-align:left; color:#e63946; font-size:.75rem; font-weight:700; text-transform:uppercase; }
  .cards-table th:last-child { width:80px; text-align:center; }
  .cards-table td { padding:8px 10px; border-bottom:1px solid #1a1a1a; }
  .cards-table tr:last-child td { border-bottom:none; }
  .cards-table tr:hover { background:#161616; }
  .cards-count { text-align:center; font-weight:800; color:#e63946; font-size:1.1rem; }

  /* Tarjetas partido */
  .match-card { background:var(--grey); border:1px solid #2a2a2a; border-left:4px solid var(--gold); border-radius:10px; padding:10px 14px; margin-bottom:8px; display:grid; grid-template-columns:1fr auto 1fr; gap:10px; align-items:center; font-size:.95rem; }
  .match-card.spartan { border-left-color:var(--red); }
  .match-card.proximo { border-left-color:#5566ff; }
  .team-local  { text-align:right; }
  .team-visita { text-align:left; }
  .score { background:var(--black); color:var(--gold); border:1px solid var(--gold); border-radius:6px; padding:2px 10px; font-weight:800; min-width:60px; text-align:center; }
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

  /* Próximos */
  .proximos-header { color:#8888ff; font-weight:700; font-size:.85rem; margin-bottom:6px; text-transform:uppercase; letter-spacing:.1em; }

  /* FOOTER */
  .compact-footer { margin-top:2rem; padding-top:16px; border-top:1px solid #1a1a1a; display:flex; flex-direction:column; gap:12px; }
  .social-section, .sponsors-section { display:flex; flex-direction:column; align-items:center; gap:6px; }
  .social-label, .sponsors-label { color:#666; font-size:.68rem; letter-spacing:.08em; font-weight:500; }
  .social-icons { display:flex; gap:10px; }
  .social-icon { width:32px; height:32px; display:flex; align-items:center; justify-content:center; background:transparent; border:1px solid #333; border-radius:50%; color:#666; font-size:1rem; transition:all .2s; text-decoration:none; }
  .social-icon:hover { color:var(--gold); border-color:var(--gold); transform:translateY(-2px); }
  .sponsors-row { display:flex; justify-content:center; align-items:center; gap:14px; flex-wrap:wrap; }
  .sponsor-link { display:flex; align-items:center; justify-content:center; height:55px; padding:0 4px; transition:transform .25s; text-decoration:none; }
  .sponsor-link:hover { transform:scale(1.08); }
  .sponsor-logo { object-fit:contain; }
  .sponsor-logo.mp { max-height:48px; max-width:90px; }
  .sponsor-logo.ink { max-height:55px; max-width:100px; }
  .sponsor-logo.bal { max-height:50px; max-width:110px; }
  .footer-credit { text-align:center; color:#444; font-size:.68rem; line-height:1.4; margin-top:4px; }
  .footer-credit b { color:#666; font-weight:600; }

  footer, #MainMenu { visibility:hidden; }

  /* Histórico */
  .hist-card {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
  }
  .hist-card h4 { margin-bottom: 8px; }
  .hist-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: #1e1e1e;
    border-radius: 8px;
    margin-bottom: 6px;
    border-left: 3px solid #f5c518;
  }
  .hist-stat:last-child { margin-bottom: 0; }
  .hist-stat .name { font-weight: 700; color: #fff; font-size: .9rem; }
  .hist-stat .value { color: #f5c518; font-weight: 800; font-size: 1.1rem; }
  .hist-stat .detail { color: #888; font-size: .75rem; }
  .rival-row {
    display: grid;
    grid-template-columns: 1fr auto auto auto auto;
    gap: 8px;
    padding: 8px 12px;
    background: #1e1e1e;
    border-radius: 8px;
    margin-bottom: 6px;
    align-items: center;
    font-size: .85rem;
  }
  .rival-row .rival-name { font-weight: 700; color: #fff; }
  .rival-row .stat-g { color: #4ade80; font-weight: 700; text-align: center; }
  .rival-row .stat-e { color: #f5c518; font-weight: 700; text-align: center; }
  .rival-row .stat-p { color: #f87171; font-weight: 700; text-align: center; }
  .rival-row .stat-pj { color: #888; font-weight: 600; text-align: center; }
  .rival-header {
    display: grid;
    grid-template-columns: 1fr auto auto auto auto;
    gap: 8px;
    padding: 4px 12px;
    font-size: .7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: .05em;
    font-weight: 700;
  }
  .no-data-msg {
    text-align: center;
    color: #666;
    padding: 30px;
    font-size: .9rem;
  }

  @media (max-width:480px) {
    .hero-title  { font-size:1.4rem; }
    .match-card { font-size:.82rem; padding:8px 10px; }
    .kpis { grid-template-columns:repeat(3, 1fr); }
    .kpi .value { font-size:1.2rem; }
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Lectura de datos desde Google Sheets
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


def _sheet_url(tab_name: str) -> str:
    """Genera URL para leer una pestaña del Google Sheet como CSV."""
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab_name}"


@st.cache_data(ttl=60, show_spinner="Cargando datos...")
def load_sheet_csv(tab_name: str) -> pd.DataFrame:
    """Lee una pestaña del Google Sheet como DataFrame."""
    try:
        url = _sheet_url(tab_name)
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.warning(f"No se pudo cargar la pestaña '{tab_name}': {e}")
        return pd.DataFrame()


def load_results(serie: str) -> pd.DataFrame:
    """Carga resultados de una serie desde Google Sheets."""
    tab_name = TABS[serie]["resultados"]
    df = load_sheet_csv(tab_name)

    if df.empty:
        return df

    # Verificar columnas necesarias
    required = ["Fase", "Local", "Visita", "Fecha"]
    if not all(col in df.columns for col in required):
        st.warning(f"La pestaña '{tab_name}' no tiene las columnas requeridas: {required}")
        return pd.DataFrame()

    # Limpiar filas separadoras
    df = df[df["Local"].astype(str).str.strip() != "---"].copy()

    # Limpiar columnas de texto
    for col in ["Fase", "Fecha", "Local", "Visita", "Goles Spartan", "Asistencia Spartan", "Hora"]:
        if col in df.columns:
            df[col] = df[col].map(_clean)

    # Eliminar filas sin Fase
    df = df[df["Fase"] != ""].reset_index(drop=True)

    return df


def load_players(serie: str) -> pd.DataFrame:
    """Carga lista de jugadores de una serie desde Google Sheets."""
    tab_name = TABS[serie]["plantel"]
    df = load_sheet_csv(tab_name)

    if df.empty:
        return pd.DataFrame()

    # Normalizar nombres de columnas a MAYÚSCULAS para evitar problemas
    col_map = {}
    for col in df.columns:
        col_upper = col.strip().upper()
        # Mapear variantes comunes
        if "POSICI" in col_upper:
            col_map[col] = "POSICIÓN"
        elif col_upper == "NOMBRES" or col_upper == "NOMBRE":
            col_map[col] = "NOMBRES"
        elif col_upper == "APELLIDOS" or col_upper == "APELLIDO":
            col_map[col] = "APELLIDOS"
        elif "CAMISETA" in col_upper or "NÚMERO" in col_upper and "CAMISETA" in col_upper:
            col_map[col] = "NÚMERO DE CAMISETA"
        elif col_upper == "RUT":
            col_map[col] = "RUT"
        elif "NACIMIENTO" in col_upper or "FECHA DE NACI" in col_upper:
            col_map[col] = "FECHA DE NACIMIENTO"
        elif "TARJETA" in col_upper and "ROJA" in col_upper:
            col_map[col] = "TARJETAS ROJAS"
        elif "NOMBRE COMPLETO" in col_upper:
            col_map[col] = "NOMBRE COMPLETO"

    df = df.rename(columns=col_map)

    if "NOMBRES" not in df.columns:
        return pd.DataFrame()

    df = df[df["NOMBRES"].astype(str).str.strip() != ""].copy()
    df = df[df["NOMBRES"] != "NOMBRES"].reset_index(drop=True)

    # Parsear posición y rol
    def parse_position_role(pos_str):
        if pd.isna(pos_str):
            return "???", None
        pos_str = str(pos_str).strip()
        if pos_str.upper() == "DT":
            return "DT", "DT"
        if "AYUDANTE" in pos_str.upper():
            return "Ayudante", "Ayudante"
        if "(" in pos_str:
            parts = pos_str.split("(")
            pos = parts[0].strip()
            rol_part = parts[1].replace(")", "").strip()
            if "CAPITAN" in rol_part.upper() or rol_part.upper() == "C":
                return pos, "Capitán"
            return pos, None
        return pos_str, None

    df[["Posicion", "Rol"]] = df["POSICIÓN"].apply(
        lambda x: pd.Series(parse_position_role(x))
    )

    # Usar "NOMBRE COMPLETO" del Sheet si existe, sino construirlo
    if "NOMBRE COMPLETO" in df.columns and df["NOMBRE COMPLETO"].notna().any():
        df["NombreCompleto"] = df["NOMBRE COMPLETO"].fillna("").str.strip()
    else:
        df["NombreCompleto"] = (
            df["NOMBRES"].fillna("").str.strip() + " " +
            df["APELLIDOS"].fillna("").str.strip()
        ).str.strip()

    df["Numero"] = pd.to_numeric(df["NÚMERO DE CAMISETA"], errors="coerce").fillna(0)
    df["FechaNac"] = pd.to_datetime(df["FECHA DE NACIMIENTO"], errors="coerce", dayfirst=True)
    df["TarjetasRojas"] = pd.to_numeric(df["TARJETAS ROJAS"], errors="coerce").fillna(0).astype(int)

    pos_order = {"POR": 1, "DEF": 2, "MED": 3, "DEL": 4, "DT": 5, "Ayudante": 6}
    df["PosOrden"] = df["Posicion"].map(lambda x: pos_order.get(x.upper() if isinstance(x, str) else x, 99))
    df = df.sort_values(["PosOrden", "Numero"]).reset_index(drop=True)

    return df


def load_penalizations(serie: str) -> dict[str, dict[str, int]]:
    """Carga penalizaciones agrupadas por fase.

    Devuelve: {"Regular": {"Julieta": 7}, "Copa de Oro": {}, ...}
    """
    tab_name = TABS[serie]["penalizaciones"]
    df = load_sheet_csv(tab_name)

    out: dict[str, dict[str, int]] = {}

    if df.empty or "Equipo" not in df.columns or "Penalización" not in df.columns:
        return out

    # Si no tiene columna Fase, asumir "Regular" para todo
    if "Fase" not in df.columns:
        penal: dict[str, int] = {}
        for _, row in df.iterrows():
            equipo = _clean(row["Equipo"])
            if not equipo:
                continue
            try:
                pts = int(row["Penalización"])
            except (ValueError, TypeError):
                continue
            if pts != 0:
                penal[equipo] = penal.get(equipo, 0) + pts
        out["Regular"] = penal
        return out

    # Con columna Fase
    for _, row in df.iterrows():
        fase = _clean(row["Fase"]) or "Regular"
        equipo = _clean(row["Equipo"])
        if not equipo:
            continue
        try:
            pts = int(row["Penalización"])
        except (ValueError, TypeError):
            continue
        if pts != 0:
            if fase not in out:
                out[fase] = {}
            out[fase][equipo] = out[fase].get(equipo, 0) + pts

    return out


def get_birthdays_this_month(df_players: pd.DataFrame) -> list[dict]:
    """Obtiene cumpleaños del mes actual."""
    if df_players.empty or "FechaNac" not in df_players.columns:
        return []

    mes_actual = datetime.now().month
    df_mes = df_players[df_players["FechaNac"].dt.month == mes_actual].copy()

    cumples = []
    for _, row in df_mes.iterrows():
        cumples.append({
            "Nombre": row["NombreCompleto"],
            "Dia": row["FechaNac"].day,
            "Mes": row["FechaNac"].month,
            "Edad": datetime.now().year - row["FechaNac"].year,
        })

    cumples.sort(key=lambda x: x["Dia"])
    return cumples


# --------------------------------------------------------------------------- #
# Supabase - Datos históricos
# --------------------------------------------------------------------------- #

def _supabase_config() -> tuple[str, str] | None:
    """Obtiene URL y key de Supabase desde st.secrets."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return url, key
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def query_supabase(table: str, params: str = "") -> pd.DataFrame:
    """Consulta una tabla o vista de Supabase via REST API."""
    import urllib.request
    import json

    config = _supabase_config()
    if not config:
        return pd.DataFrame()

    url_base, key = config
    url = f"{url_base}/rest/v1/{table}?select=*"
    if params:
        url += f"&{params}"

    req = urllib.request.Request(url, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })

    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


def load_goleadores_historicos() -> pd.DataFrame:
    """Carga ranking histórico de goleadores desde Supabase."""
    df = query_supabase("v_goleadores_historicos")
    if not df.empty:
        df = df.sort_values("goles_totales", ascending=False).reset_index(drop=True)
    return df


def load_historial_rivales() -> pd.DataFrame:
    """Carga historial de Spartan contra cada rival desde Supabase."""
    df = query_supabase("v_historial_rivales")
    if not df.empty:
        df = df.sort_values("partidos", ascending=False).reset_index(drop=True)
    return df


def load_torneos_historicos() -> pd.DataFrame:
    """Carga lista de torneos archivados."""
    return query_supabase("torneos", "order=anio.desc,nombre.desc")


def load_partidos_torneo(torneo_nombre: str, serie: str) -> pd.DataFrame:
    """Carga partidos de un torneo específico desde Supabase."""
    import urllib.parse

    # Consulta con joins
    config = _supabase_config()
    if not config:
        return pd.DataFrame()

    import urllib.request
    import json

    url_base, key = config

    # Obtener fase_id
    fases_df = query_supabase("fases", f"serie=eq.{serie}&torneo_id=in.(select id from torneos where nombre=eq.{urllib.parse.quote(torneo_nombre)})")

    # Usar approach más simple: cargar partidos con equipo info
    url = (
        f"{url_base}/rest/v1/partidos?"
        f"select=fecha_numero,goles_local,goles_visita,"
        f"local:equipos!partidos_local_id_fkey(nombre),"
        f"visita:equipos!partidos_visita_id_fkey(nombre),"
        f"fase:fases!inner(nombre,serie,torneo:torneos!inner(nombre))"
        f"&fase.torneo.nombre=eq.{urllib.parse.quote(torneo_nombre)}"
        f"&fase.serie=eq.{serie}"
        f"&order=fecha_numero.asc"
    )

    req = urllib.request.Request(url, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })

    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        if not data:
            return pd.DataFrame()

        rows = []
        for d in data:
            rows.append({
                "Fecha": d.get("fecha_numero", ""),
                "Local": d.get("local", {}).get("nombre", ""),
                "Visita": d.get("visita", {}).get("nombre", ""),
                "Goles L": d.get("goles_local"),
                "Goles V": d.get("goles_visita"),
                "Fase": d.get("fase", {}).get("nombre", ""),
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


# --------------------------------------------------------------------------- #
# Cálculos
# --------------------------------------------------------------------------- #

def compute_standings(df: pd.DataFrame, penalizaciones: dict[str, int] | None = None) -> pd.DataFrame:
    """Calcula tabla de posiciones con penalizaciones opcionales."""
    penalizaciones = penalizaciones or {}
    stats: dict[str, dict] = defaultdict(
        lambda: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0}
    )
    for _, row in df.iterrows():
        local, visita = _clean(row["Local"]), _clean(row["Visita"])
        gl, gv = row.get("Goles L"), row.get("Goles V")
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
        pts_base = s["PG"] * 3 + s["PE"]
        penal = penalizaciones.get(team, 0)
        if not penal:
            for eq_penal, pts_penal in penalizaciones.items():
                if eq_penal.strip().lower() == team.strip().lower():
                    penal = pts_penal
                    break
        rows.append({
            "Equipo": team, "PJ": s["PJ"], "PG": s["PG"], "PE": s["PE"],
            "PP": s["PP"], "GF": s["GF"], "GC": s["GC"],
            "DIF": s["GF"] - s["GC"], "Pts": pts_base - penal,
            "Penalizado": penal > 0,
        })

    if not rows:
        return pd.DataFrame(columns=["Pos", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DIF", "Pts", "Penalizado"])

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
        for p in _parse_players(_clean(row.get("Goles Spartan", ""))):
            goles[p] += 1
        for p in _parse_players(_clean(row.get("Asistencia Spartan", ""))):
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
        is_local = SPARTAN_NAME in str(row["Local"])
        rival = row["Visita"] if is_local else row["Local"]
        gl = row.get("Goles L")
        gv = row.get("Goles V")
        if pd.notna(gl) and pd.notna(gv):
            gf = int(gl) if is_local else int(gv)
            gc = int(gv) if is_local else int(gl)
            res = "G" if gf > gc else ("E" if gf == gc else "P")
            played.append({
                "Fecha": _clean(row["Fecha"]), "Rival": _clean(rival),
                "Local": is_local, "GF": gf, "GC": gc, "Res": res,
            })
        else:
            dia = row.get("Día") if "Día" in df.columns and pd.notna(row.get("Día")) else None
            hora = _clean(row.get("Hora", "")) if "Hora" in df.columns else None
            upcoming.append({
                "Fecha": _clean(row["Fecha"]), "Rival": _clean(rival),
                "EsLocal": is_local, "Dia": dia, "Hora": hora or None,
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


def get_fases_con_datos(df: pd.DataFrame) -> list[str]:
    """Devuelve las fases que tienen al menos 1 fila con datos."""
    if df.empty or "Fase" not in df.columns:
        return ["Regular"]
    fases = df["Fase"].unique().tolist()
    return [f for f in fases if f and str(f).strip()]


def filter_by_fase(df: pd.DataFrame, fase: str) -> pd.DataFrame:
    """Filtra DataFrame por fase."""
    if "Fase" not in df.columns:
        return df
    return df[df["Fase"] == fase].reset_index(drop=True)


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
    return f'<span class="spartan-name">{name}</span>' if SPARTAN_NAME in str(name) else str(name)


def render_birthdays(cumples: list[dict]):
    if not cumples:
        st.info("No hay cumpleaños este mes.")
        return

    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
        7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    mes_nombre = meses[cumples[0]["Mes"]]

    st.markdown(f"### 🎂 Cumpleaños de {mes_nombre.capitalize()}")
    st.caption(f"Total: {len(cumples)} cumpleaños este mes")
    st.markdown("")

    html_parts = []
    for c in cumples:
        html_parts.append(
            f'<div class="birthday-item">'
            f'<div class="birthday-name">{c["Nombre"]}</div>'
            f'<div class="birthday-date">{c["Dia"]} de {mes_nombre} · {c["Edad"]} años</div>'
            f'</div>'
        )
    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def render_red_cards(df: pd.DataFrame):
    df_rojas = df[df["TarjetasRojas"] > 0].copy()
    df_rojas = df_rojas.sort_values("TarjetasRojas", ascending=False)

    if df_rojas.empty:
        st.info("No hay tarjetas rojas registradas.")
        return

    st.markdown("### 🟥 Tabla Disciplinaria")
    st.caption(f"Jugadores con tarjetas rojas: {len(df_rojas)}")
    st.markdown("")

    html_parts = ['<table class="cards-table"><thead><tr>']
    html_parts.append('<th>Jugador</th><th>Rojas</th>')
    html_parts.append('</tr></thead><tbody>')
    for _, row in df_rojas.iterrows():
        html_parts.append(f'<tr><td>{row["NombreCompleto"]}</td>')
        html_parts.append(f'<td class="cards-count">{int(row["TarjetasRojas"])}</td></tr>')
    html_parts.append('</tbody></table>')
    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def render_roster_table(df: pd.DataFrame):
    if df.empty:
        st.info("Sin jugadores registrados.")
        return

    st.markdown("### 👥 Plantel")
    st.caption(f"Total: {len(df)} jugadores registrados")
    st.markdown("")

    html_parts = ['<table class="roster-table"><thead><tr>']
    html_parts.append('<th>#</th><th>Jugador</th><th>Pos</th>')
    html_parts.append('</tr></thead><tbody>')

    for _, row in df.iterrows():
        num = row["Numero"]
        num_html = f'<div class="num-badge">{int(num)}</div>' if num > 0 else '<div class="num-badge sn">S/N</div>'
        nombre = row["NombreCompleto"]
        rol = row["Rol"]
        if rol == "DT":
            nombre_html = f'{nombre} <span class="role-tag dt">DT</span>'
        elif rol == "Capitán":
            nombre_html = f'{nombre} <span class="role-tag cap">C</span>'
        elif rol == "Ayudante":
            nombre_html = f'{nombre} <span class="role-tag ayu">Ayu</span>'
        else:
            nombre_html = nombre
        pos = row["Posicion"]
        pos_display = {"POR": "POR", "DEF": "DEF", "MED": "MED", "DEL": "DEL", "DT": "DT", "Ayudante": "Ayu"}.get(pos, pos)
        html_parts.append(f'<tr><td style="text-align:center;">{num_html}</td>')
        html_parts.append(f'<td>{nombre_html}</td>')
        html_parts.append(f'<td style="text-align:center;"><span class="pos-badge">{pos_display}</span></td></tr>')
    html_parts.append('</tbody></table>')
    st.markdown(''.join(html_parts), unsafe_allow_html=True)


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

    kpis_data = [
        ("Posición", f"{int(s['Pos'])}°"),
        ("Puntos", int(s["Pts"])),
        ("PJ", int(s["PJ"])),
        ("GF", int(s["GF"])),
        ("GC", int(s["GC"])),
    ]
    kpis_html = '<div class="kpis">'
    for label, value in kpis_data:
        kpis_html += f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>'
    kpis_html += '</div>'
    st.markdown(kpis_html, unsafe_allow_html=True)


def render_standings(tabla: pd.DataFrame, corte_pos: int | None = None, corte_labels: tuple[str, str] | None = None):
    """Renderiza tabla de posiciones con línea de corte opcional."""
    if tabla.empty:
        st.info("Sin partidos jugados aún.")
        return

    medal = {1: "🥇", 2: "🥈", 3: "🥉"}
    html = '<table class="standings-table"><thead><tr>'
    for col in ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DIF", "Pts"]:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    # Etiqueta de zona arriba de la tabla si hay corte
    if corte_pos and corte_labels:
        html = f'<div class="cutline-label oro">🏆 {corte_labels[0]}</div>' + html

    penalizados = []
    tiene_penal_col = "Penalizado" in tabla.columns

    for _, row in tabla.iterrows():
        is_spartan = SPARTAN_NAME in row["Equipo"]
        pos = int(row["Pos"])
        pos_str = medal.get(pos, str(pos))
        dif_val = int(row["DIF"])
        dif_str = f"+{dif_val}" if dif_val > 0 else str(dif_val)

        es_penalizado = bool(row["Penalizado"]) if tiene_penal_col else False
        if es_penalizado:
            penalizados.append(row["Equipo"])

        # Clase de fila
        tr_classes = []
        if is_spartan:
            tr_classes.append("row-spartan")
        if corte_pos and pos == corte_pos:
            tr_classes.append("cutline-row")
        tr_class = " ".join(tr_classes)

        nombre_eq = row["Equipo"]
        if es_penalizado:
            nombre_eq += ' <span class="penal-mark">*</span>'
        equipo_str = f"⚔️ {nombre_eq}" if is_spartan else nombre_eq

        html += f'<tr class="{tr_class}">'
        html += f"<td>{pos_str}</td>"
        html += f"<td>{equipo_str}</td>"
        for col in ["PJ", "PG", "PE", "PP", "GF", "GC"]:
            html += f"<td>{int(row[col])}</td>"
        html += f"<td>{dif_str}</td>"
        html += f"<td><b>{int(row['Pts'])}</b></td>"
        html += "</tr>"

        # Insertar etiqueta de zona después de la línea de corte
        if corte_pos and pos == corte_pos and corte_labels:
            html += f'<tr><td colspan="10"><div class="cutline-label plata">🥈 {corte_labels[1]}</div></td></tr>'

    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

    # Nota al pie si hay penalizados
    if penalizados:
        if len(penalizados) == 1:
            equipos_txt = penalizados[0]
        elif len(penalizados) == 2:
            equipos_txt = f"{penalizados[0]} y {penalizados[1]}"
        else:
            equipos_txt = ", ".join(penalizados[:-1]) + f" y {penalizados[-1]}"
        verbo = "recibió" if len(penalizados) == 1 else "recibieron"
        st.markdown(
            f'<div class="penal-note">'
            f'<span class="penal-mark">*</span> {equipos_txt} {verbo} '
            f'descuento de puntos por temas administrativos.'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_fixture(df: pd.DataFrame):
    if df.empty:
        st.info("Sin partidos cargados.")
        return
    for fecha, grupo in df.groupby("Fecha", sort=False):
        st.markdown(f'<span class="fecha-chip">{fecha}</span>', unsafe_allow_html=True)
        for _, row in grupo.iterrows():
            local, visita = _clean(row["Local"]), _clean(row["Visita"])
            gl, gv = _fmt(row.get("Goles L")), _fmt(row.get("Goles V"))
            is_spartan = SPARTAN_NAME in local or SPARTAN_NAME in visita
            played = gl != "-" and gv != "-"
            card_cls = "match-card spartan" if is_spartan else "match-card"
            score_cls = "score" if played else "score pending"
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

    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for m in upcoming[:6]:
        local_name = SPARTAN_NAME if m["EsLocal"] else m["Rival"]
        visita_name = m["Rival"] if m["EsLocal"] else SPARTAN_NAME
        condicion = "🏠 Local" if m["EsLocal"] else "✈️ Visita"

        info_parts = [m["Fecha"]]
        if m.get("Dia"):
            try:
                fecha_dt = pd.to_datetime(m["Dia"])
                if pd.notna(fecha_dt):
                    info_parts.append(f"{dias_semana[fecha_dt.weekday()]} {fecha_dt.day} {meses[fecha_dt.month]}")
            except Exception:
                pass
        if m.get("Hora"):
            info_parts.append(m["Hora"])
        info_parts.append(condicion)

        st.markdown(
            f'<div class="match-card proximo">'
            f'<div class="team-local">{_hl(local_name)}</div>'
            f'<div class="score pending">vs</div>'
            f'<div class="team-visita">{_hl(visita_name)}</div>'
            f'</div>'
            f'<div style="text-align:center;margin:-4px 0 8px;font-size:.75rem;color:#666;">'
            f'{" · ".join(info_parts)}</div>',
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
                f"<tr><td>{medal_str}</td>"
                f"<td>{row['Jugador']}</td>"
                f"<td style='text-align:center;color:#f5c518;font-weight:800;'>{int(row[col])}</td></tr>"
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
    fig.add_trace(go.Scatter(
        x=f_plot, y=p_plot,
        fill="tozeroy", fillcolor="rgba(245,197,24,0.07)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
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
        title=dict(text=f"📈 Evolución de Puntos — {categoria}", font=dict(color="#f5c518", size=14), x=0.5),
        paper_bgcolor="#0b0b0b", plot_bgcolor="#0b0b0b",
        font=dict(color="#cccccc"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#1e1e1e", tickfont=dict(size=11), dtick=1, rangemode="tozero"),
        margin=dict(l=20, r=20, t=50, b=30),
        height=300, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<div style="display:flex;gap:16px;justify-content:center;margin-bottom:12px;font-size:.78rem;">'
        '<span>🟢 Victoria</span><span>🟡 Empate</span><span>🔴 Derrota</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Detalle de partidos jugados</div>', unsafe_allow_html=True)
    for m in played:
        color = "#4ade80" if m["Res"] == "G" else ("#f5c518" if m["Res"] == "E" else "#f87171")
        label = "Victoria" if m["Res"] == "G" else ("Empate" if m["Res"] == "E" else "Derrota")
        cond = "🏠" if m["Local"] else "✈️"
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 12px;background:#1e1e1e;border-radius:8px;margin-bottom:5px;'
            f'border-left:3px solid {color};">'
            f'<span style="font-size:.85rem;">{cond} {m["Fecha"]} · vs {m["Rival"]}</span>'
            f'<span style="font-weight:800;color:{color};font-size:.9rem;">'
            f'{m["GF"]}–{m["GC"]} <span style="font-size:.72rem;opacity:.8;">({label})</span></span></div>',
            unsafe_allow_html=True,
        )


def render_footer():
    mp_data = _logo_b64(str(SPONSOR_MP))
    ink_data = _logo_b64(str(SPONSOR_INK))
    bal_data = _logo_b64(str(SPONSOR_BAL))

    footer_parts = ['<div class="compact-footer">']
    footer_parts.append('<div class="social-section">')
    footer_parts.append('<div class="social-label">Síguenos en nuestras redes sociales</div>')
    footer_parts.append('<div class="social-icons">')
    footer_parts.append(f'<a href="{INSTAGRAM_URL}" class="social-icon" target="_blank" title="Instagram">')
    footer_parts.append('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">')
    footer_parts.append('<rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>')
    footer_parts.append('<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>')
    footer_parts.append('<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>')
    footer_parts.append('</svg></a></div></div>')

    footer_parts.append('<div class="sponsors-section">')
    footer_parts.append('<div class="sponsors-label">Con el auspicio de:</div>')
    footer_parts.append('<div class="sponsors-row">')
    footer_parts.append(f'<a href="{MPRENTAL_URL}" class="sponsor-link" target="_blank" title="MP Rental">')
    footer_parts.append(f'<img src="{mp_data}" alt="MP Rental" class="sponsor-logo mp"></a>')
    footer_parts.append(f'<a href="{INKUBIERTOS_URL}" class="sponsor-link" target="_blank" title="Inkubiertos">')
    footer_parts.append(f'<img src="{ink_data}" alt="Inkubiertos" class="sponsor-logo ink"></a>')
    footer_parts.append(f'<a href="{BALDOMEROS_URL}" class="sponsor-link" target="_blank" title="Baldomero\'s">')
    footer_parts.append(f'<img src="{bal_data}" alt="Baldomero\'s" class="sponsor-logo bal"></a>')
    footer_parts.append('</div></div>')

    footer_parts.append('<div class="footer-credit">')
    footer_parts.append('<b>Spartan FC App</b><br>')
    footer_parts.append('Desarrollado por Boris Bugueño B.')
    footer_parts.append('</div></div>')

    st.markdown(''.join(footer_parts), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Tab Histórico
# --------------------------------------------------------------------------- #

def render_goleadores_historicos():
    """Renderiza ranking de goleadores históricos."""
    df = load_goleadores_historicos()
    if df.empty:
        st.markdown('<div class="no-data-msg">No hay datos históricos disponibles aún.</div>', unsafe_allow_html=True)
        return

    st.markdown("### 🥅 Goleadores Históricos de Spartan")
    st.caption(f"Ranking acumulado en todos los campeonatos")
    st.markdown("")

    medals = ["🥇", "🥈", "🥉"]
    html_parts = []
    for i, (_, row) in enumerate(df.iterrows()):
        pos = medals[i] if i < 3 else f"{i+1}."
        torneos_txt = f"{int(row['torneos_jugados'])} torneo{'s' if row['torneos_jugados'] > 1 else ''}"
        html_parts.append(
            f'<div class="hist-stat">'
            f'<div><span style="margin-right:8px;">{pos}</span>'
            f'<span class="name">{row["jugador"]}</span>'
            f'<br><span class="detail">{torneos_txt}</span></div>'
            f'<div class="value">{int(row["goles_totales"])}</div>'
            f'</div>'
        )

    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def render_historial_rivales():
    """Renderiza historial de Spartan contra cada rival."""
    df = load_historial_rivales()
    if df.empty:
        st.markdown('<div class="no-data-msg">No hay datos históricos disponibles aún.</div>', unsafe_allow_html=True)
        return

    st.markdown("### ⚔️ Historial contra Rivales")
    st.caption("Record histórico de Spartan F.C.")
    st.markdown("")

    # Header
    html = '<div class="rival-header">'
    html += '<div>Rival</div><div style="text-align:center;">PJ</div>'
    html += '<div style="text-align:center;">G</div><div style="text-align:center;">E</div>'
    html += '<div style="text-align:center;">P</div></div>'

    for _, row in df.iterrows():
        v = int(row["victorias"])
        e = int(row["empates"])
        d = int(row["derrotas"])
        pj = int(row["partidos"])
        gf = int(row["gf"])
        gc = int(row["gc"])

        html += f'<div class="rival-row">'
        html += f'<div class="rival-name">{row["rival"]}<br><span class="detail">{gf} GF · {gc} GC</span></div>'
        html += f'<div class="stat-pj">{pj}</div>'
        html += f'<div class="stat-g">{v}</div>'
        html += f'<div class="stat-e">{e}</div>'
        html += f'<div class="stat-p">{d}</div>'
        html += f'</div>'

    st.markdown(html, unsafe_allow_html=True)


def render_torneos_anteriores(serie: str):
    """Renderiza resumen de torneos archivados."""
    df_torneos = load_torneos_historicos()
    if df_torneos.empty:
        st.markdown('<div class="no-data-msg">No hay torneos archivados aún.</div>', unsafe_allow_html=True)
        return

    st.markdown("### 🏆 Torneos Anteriores")
    st.caption("Resultados archivados por campeonato")
    st.markdown("")

    for _, torneo in df_torneos.iterrows():
        torneo_nombre = torneo["nombre"]
        with st.expander(f"🏆 {torneo_nombre}", expanded=False):
            df_partidos = load_partidos_torneo(torneo_nombre, serie)
            if df_partidos.empty:
                st.caption(f"Sin partidos registrados en Serie {serie}")
                continue

            # Calcular tabla de posiciones del torneo histórico
            tabla = compute_standings(df_partidos)
            if not tabla.empty:
                render_standings(tabla)

            # Mostrar resultados de Spartan
            spartan_mask = (
                df_partidos["Local"].str.contains(SPARTAN_NAME, na=False) |
                df_partidos["Visita"].str.contains(SPARTAN_NAME, na=False)
            )
            df_spartan = df_partidos[spartan_mask]
            if not df_spartan.empty:
                jugados = df_spartan[df_spartan["Goles L"].notna()]
                if not jugados.empty:
                    st.markdown(f"**Partidos de Spartan:** {len(jugados)} jugados")
                    for _, row in jugados.iterrows():
                        gl = int(row["Goles L"]) if pd.notna(row["Goles L"]) else "-"
                        gv = int(row["Goles V"]) if pd.notna(row["Goles V"]) else "-"
                        st.markdown(
                            f'<div class="match-card">'
                            f'<div class="team-local">{_hl(row["Local"])}</div>'
                            f'<div class="score">{gl} · {gv}</div>'
                            f'<div class="team-visita">{_hl(row["Visita"])}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )


def render_historico_tab(serie: str):
    """Renderiza el tab completo de Histórico."""
    config = _supabase_config()
    if not config:
        st.warning("⚠️ Supabase no está configurado. Agrega las credenciales en Settings → Secrets de Streamlit Cloud.")
        return

    sub_tabs = st.tabs(["🥅 Goleadores", "⚔️ vs Rivales", "🏆 Torneos"])

    with sub_tabs[0]:
        render_goleadores_historicos()
    with sub_tabs[1]:
        render_historial_rivales()
    with sub_tabs[2]:
        render_torneos_anteriores(serie)


# --------------------------------------------------------------------------- #
# Tab Estadísticas
# --------------------------------------------------------------------------- #

def render_estadisticas_tab(df_fase: pd.DataFrame, titulo: str, penalizaciones: dict[str, int] | None = None,
                            corte_pos: int | None = None, corte_labels: tuple[str, str] | None = None):
    """Renderiza tab Estadísticas con sus sub-tabs."""
    tabla = compute_standings(df_fase, penalizaciones)
    gol, asist = compute_individual_stats(df_fase)
    played, upcoming = get_spartan_matches(df_fase)

    spartan_row = tabla[tabla["Equipo"].str.contains(SPARTAN_NAME, na=False)]
    if not spartan_row.empty and int(spartan_row.iloc[0]["Pos"]) == 1:
        render_leader_banner()

    render_kpis(tabla, played)
    st.markdown("")

    sub_tabs = st.tabs(["📊 Posiciones", "📅 Fixture", "⭐ Individuales", "📈 Evolución", "🔜 Próximos"])

    with sub_tabs[0]:
        render_standings(tabla, corte_pos, corte_labels)
    with sub_tabs[1]:
        render_fixture(df_fase)
    with sub_tabs[2]:
        render_individuals(gol, asist)
    with sub_tabs[3]:
        render_evolution(played, titulo)
    with sub_tabs[4]:
        render_upcoming(upcoming)


# --------------------------------------------------------------------------- #
# App principal
# --------------------------------------------------------------------------- #

def main():
    # Header
    logo_data = _logo_b64(str(LOGO_PATH))
    if not logo_data:
        logo_data = _logo_b64(str(LOGO_FALLBACK))
    logo_html = f'<img src="{logo_data}" alt="Spartan FC">' if logo_data else "⚔️"

    hero_parts = ['<div class="hero-v6">']
    hero_parts.append(f'<div class="hero-logo">{logo_html}</div>')
    hero_parts.append('<div class="hero-accent"></div>')
    hero_parts.append('<div class="hero-text">')
    hero_parts.append('<div class="hero-title">SPARTAN <span class="accent-word">FC</span></div>')
    hero_parts.append('<div class="hero-subtitle">')
    hero_parts.append('<span class="live-dot"></span>')
    hero_parts.append('Temporada 2026')
    hero_parts.append('</div></div>')
    hero_parts.append('</div>')
    st.markdown(''.join(hero_parts), unsafe_allow_html=True)

    # Selector de categoría
    series = ["35", "45"]
    serie_labels = {"35": "Serie 35", "45": "Serie 45"}

    st.markdown('<div class="selector-container">', unsafe_allow_html=True)
    st.markdown('<div class="selector-label">Categoría</div>', unsafe_allow_html=True)

    serie = st.selectbox(
        "Categoría",
        options=series,
        format_func=lambda x: serie_labels[x],
        label_visibility="collapsed",
        key="serie_selector"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Cargar datos de la serie seleccionada
    df_resultados = load_results(serie)
    df_players = load_players(serie)
    penalizaciones_data = load_penalizations(serie)

    if df_resultados.empty:
        st.warning("No se encontraron datos de resultados para esta serie. Verifica que la pestaña del Google Sheet tenga datos.")

    # Detectar fases con datos
    fases = get_fases_con_datos(df_resultados)

    # Selector de fase (solo si hay más de una)
    fase_seleccionada = fases[0] if fases else "Regular"
    if len(fases) > 1:
        st.markdown('<div class="selector-container">', unsafe_allow_html=True)
        st.markdown('<div class="selector-label">Fase</div>', unsafe_allow_html=True)
        fase_seleccionada = st.selectbox(
            "Fase",
            options=fases,
            label_visibility="collapsed",
            key="fase_selector"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Filtrar datos por fase
    df_fase = filter_by_fase(df_resultados, fase_seleccionada)

    # Penalizaciones de esta fase
    penal_fase = penalizaciones_data.get(fase_seleccionada, {})

    # Determinar línea de corte de clasificación
    corte_pos = None
    corte_labels = None

    if serie == "35" and fase_seleccionada == "Regular":
        corte_pos = CLASIFICACION["35"]["corte_oro"]
        corte_labels = ("Zona Copa de Oro", "Zona Copa de Plata")
    elif serie == "45" and fase_seleccionada in ("Grupo A", "Grupo B"):
        corte_pos = CLASIFICACION["45"]["corte_oro_por_grupo"]
        corte_labels = ("Clasifican a Copa de Oro", "Copa de Plata")

    # 5 Tabs principales
    main_tabs = st.tabs(["📊 Estadísticas", "👥 Plantel", "🎂 Cumpleaños", "🟥 Tarjetas", "📜 Histórico"])

    with main_tabs[0]:
        if not df_fase.empty:
            titulo = f"Serie {serie} · {fase_seleccionada}"
            render_estadisticas_tab(df_fase, titulo, penal_fase, corte_pos, corte_labels)
        else:
            st.info(f"No hay partidos cargados en {fase_seleccionada}.")

    with main_tabs[1]:
        if not df_players.empty:
            render_roster_table(df_players)
        else:
            st.info("No hay datos de plantel para esta serie.")

    with main_tabs[2]:
        if not df_players.empty:
            cumples = get_birthdays_this_month(df_players)
            render_birthdays(cumples)
        else:
            st.info("No hay datos de plantel para mostrar cumpleaños.")

    with main_tabs[3]:
        if not df_players.empty:
            render_red_cards(df_players)
        else:
            st.info("No hay datos de jugadores para esta serie.")

    with main_tabs[4]:
        render_historico_tab(serie)

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
