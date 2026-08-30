import streamlit as st
import requests
import pandas as pd
import folium
# pyrefly: ignore [missing-import]
from streamlit_folium import st_folium
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FlightTracker Live",
    page_icon="assets/favicon.ico" if False else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS global
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Fondo principal */
.stApp {
    background-color: #0f1117;
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #2d3748;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label {
    color: #94a3b8 !important;
    font-size: 0.85rem;
}

/* Cabecera */
.page-header {
    padding: 1.5rem 0 1rem 0;
    border-bottom: 1px solid #2d3748;
    margin-bottom: 1.5rem;
}
.page-header h1 {
    font-size: 1.7rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.5px;
}
.page-header .subtitle {
    font-size: 0.82rem;
    color: #64748b;
    margin: 0;
}
.live-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #0f2d1f;
    border: 1px solid #166534;
    color: #4ade80;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    margin-left: 0.75rem;
    vertical-align: middle;
}
.live-badge::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4ade80;
    animation: pulse 1.8s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}

/* Tarjetas de métricas */
.metric-card {
    background: #161b27;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    height: 100%;
}
.metric-card .metric-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
}
.metric-card .metric-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
}
.metric-card .metric-sub {
    font-size: 0.75rem;
    color: #475569;
    margin-top: 0.3rem;
}

/* Sección de título */
.section-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #2d3748;
}

/* Leyenda del mapa */
.map-legend {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
    margin-top: 0.6rem;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    color: #64748b;
}
.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* Tabla Streamlit */
[data-testid="stDataFrame"] {
    border: 1px solid #2d3748;
    border-radius: 8px;
    overflow: hidden;
}

/* Ocultar toolbar de Streamlit */
[data-testid="stToolbar"] { display: none; }

/* Alertas personalizadas */
.custom-warning {
    background: #1c1408;
    border: 1px solid #854d0e;
    color: #fbbf24;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
}
.custom-info {
    background: #0c1a2e;
    border: 1px solid #1e40af;
    color: #93c5fd;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
}
.custom-error {
    background: #1c0a0a;
    border: 1px solid #991b1b;
    color: #fca5a5;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
}

/* Divisor */
hr { border-color: #2d3748 !important; }

/* Botón sidebar */
.stButton > button {
    background: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 500;
    width: 100%;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #334155;
    border-color: #475569;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────
API_URL     = "https://get-flights-api-u5qt55joha-uc.a.run.app/live/flights"
DEFAULT_TTL = 30  # segundos

# ─────────────────────────────────────────────────────────────────────────────
# Cabecera
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h1>FlightTracker <span class="live-badge">Live</span></h1>
  <p class="subtitle">Monitoreo de vuelos en tiempo real &mdash; OpenSky Network</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Configuracion**")
    st.markdown("---")
    limit = st.slider("Vuelos a mostrar", min_value=10, max_value=500,
                      value=500, step=10)
    refresh_ttl = st.selectbox("Cache TTL (segundos)", [10, 30, 60, 120],
                               index=1)
    st.markdown("---")
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown(f"**Fuente:** OpenSky Network")
    st.markdown(f"**Endpoint:** `…/live/flights`")
    st.markdown(f"**TTL activo:** {refresh_ttl} s")
    st.markdown(f"**Version Python:** 3.13+")

# ─────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=DEFAULT_TTL)
def fetch_flights(limit: int) -> tuple[pd.DataFrame, str | None]:
    """
    Obtiene vuelos desde la API y devuelve (DataFrame, error_msg).

    Formato de respuesta esperado:
        {"status": "success", "count": N, "data": [...]}

    Campos normalizados:
        - altitude  <- baro_altitude o geo_altitude
        - timestamp <- observed_at, last_seen_at o processed_at (UNIX int o ISO str)
    """
    try:
        r = requests.get(f"{API_URL}?limit={limit}", timeout=15)

        # Capturar errores HTTP con el cuerpo de la respuesta
        if not r.ok:
            try:
                detail = r.json()
                if isinstance(detail, dict) and "detail" in detail:
                    msgs = [
                        d.get("msg", str(d))
                        for d in (detail["detail"]
                                  if isinstance(detail["detail"], list)
                                  else [detail["detail"]])
                    ]
                    err = " | ".join(msgs)
                else:
                    err = str(detail)
            except Exception:
                err = r.text[:300]
            return pd.DataFrame(), f"HTTP {r.status_code}: {err}"

        raw = r.json()

        # Detectar la lista de vuelos independientemente del nombre de clave
        if isinstance(raw, list):
            flights = raw
        elif isinstance(raw, dict):
            flights = None
            for key in ("data", "flights", "states", "results"):
                if key in raw and isinstance(raw[key], list):
                    flights = raw[key]
                    break
            if flights is None:
                for v in raw.values():
                    if isinstance(v, list):
                        flights = v
                        break
            if flights is None:
                return pd.DataFrame(), "No se encontro una lista de vuelos en la respuesta de la API."
        else:
            return pd.DataFrame(), "Formato de respuesta inesperado."

        df = pd.DataFrame(flights)
        if df.empty:
            return df, None

        # Normalizar altitud
        if "altitude" not in df.columns:
            if "baro_altitude" in df.columns:
                df["altitude"] = pd.to_numeric(df["baro_altitude"], errors="coerce")
            elif "geo_altitude" in df.columns:
                df["altitude"] = pd.to_numeric(df["geo_altitude"], errors="coerce")

        # Garantizar coordenadas
        for col in ("latitude", "longitude"):
            if col not in df.columns:
                df[col] = None
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Normalizar timestamp (UNIX int o ISO string, con zonas mixtas)
        for candidate in ("timestamp", "observed_at", "last_seen_at", "processed_at"):
            if candidate in df.columns:
                converted = pd.to_datetime(df[candidate], unit="s",
                                           errors="coerce", utc=True)
                if converted.isna().all():
                    converted = pd.to_datetime(df[candidate],
                                               errors="coerce", utc=True)
                df["timestamp"] = converted
                break

        return df, None

    except requests.exceptions.Timeout:
        return pd.DataFrame(), "La solicitud supero el tiempo de espera (15 s). Intente de nuevo."
    except requests.exceptions.ConnectionError as e:
        return pd.DataFrame(), f"Error de conexion: {e}"
    except Exception as e:
        return pd.DataFrame(), f"Error inesperado: {e}"


df, fetch_error = fetch_flights(limit)

# ─────────────────────────────────────────────────────────────────────────────
# Metricas
# ─────────────────────────────────────────────────────────────────────────────
now_str   = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
total     = len(df) if not df.empty else 0
alt_valid = int(df["altitude"].notna().sum()) if not df.empty and "altitude" in df.columns else 0
avg_vel   = (f'{df["velocity"].mean():.0f} kn'
             if not df.empty and "velocity" in df.columns and df["velocity"].notna().any()
             else "N/D")
countries = (df["origin_country"].nunique()
             if not df.empty and "origin_country" in df.columns else 0)

c1, c2, c3, c4 = st.columns(4)
for col, label, value, sub in [
    (c1, "Vuelos activos",       str(total),    "en este momento"),
    (c2, "Actualizacion",        now_str,       f"TTL {refresh_ttl} s"),
    (c3, "Con altitud",          str(alt_valid), "registros validos"),
    (c4, "Paises detectados",    str(countries), "origenes distintos"),
]:
    col.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if df.empty:
    msg = fetch_error or "La API no devolvio registros para los parametros seleccionados."
    st.markdown(f"""
    <div class="custom-error">
        <strong>Sin datos disponibles</strong><br>
        {msg}
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Layout: mapa + tabla
# ─────────────────────────────────────────────────────────────────────────────
col_map, col_table = st.columns([3, 2], gap="large")

# ── Mapa ─────────────────────────────────────────────────────────────────────
with col_map:
    st.markdown('<div class="section-title">Mapa de vuelos activos</div>',
                unsafe_allow_html=True)

    has_coords = (
        "latitude"  in df.columns and
        "longitude" in df.columns and
        df["latitude"].notna().any()
    )

    if has_coords:
        plot_df     = df.dropna(subset=["latitude", "longitude"]).head(500)
        center_lat  = plot_df["latitude"].mean()
        center_lon  = plot_df["longitude"].mean()

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=3,
            tiles="CartoDB dark_matter",
        )

        ALT_COLORS = [
            (30_000, "#ef4444"),   # rojo  > 30 000 ft
            (20_000, "#f97316"),   # naranja 20–30 k
            (10_000, "#22c55e"),   # verde 10–20 k
            (0,      "#3b82f6"),   # azul  < 10 k
        ]

        def alt_color(alt_val):
            if pd.isna(alt_val):
                return "#64748b"
            for threshold, color in ALT_COLORS:
                if float(alt_val) > threshold:
                    return color
            return "#3b82f6"

        for _, row in plot_df.iterrows():
            color = alt_color(row.get("altitude"))
            callsign = str(row.get("callsign", "")).strip() or "N/D"
            popup_html = f"""
            <div style="font-family:Inter,sans-serif;font-size:13px;min-width:180px">
              <div style="font-weight:700;font-size:14px;margin-bottom:6px;
                          border-bottom:1px solid #e2e8f0;padding-bottom:4px">
                {callsign}
              </div>
              <table style="width:100%;border-collapse:collapse">
                <tr><td style="color:#64748b;padding:2px 4px">ICAO24</td>
                    <td style="padding:2px 4px">{row.get('icao24','N/D')}</td></tr>
                <tr><td style="color:#64748b;padding:2px 4px">Pais</td>
                    <td style="padding:2px 4px">{row.get('origin_country','N/D')}</td></tr>
                <tr><td style="color:#64748b;padding:2px 4px">Altitud</td>
                    <td style="padding:2px 4px">{row.get('altitude','N/D')} ft</td></tr>
                <tr><td style="color:#64748b;padding:2px 4px">Velocidad</td>
                    <td style="padding:2px 4px">{row.get('velocity','N/D')} kn</td></tr>
                <tr><td style="color:#64748b;padding:2px 4px">Rumbo</td>
                    <td style="padding:2px 4px">{row.get('heading','N/D')}</td></tr>
              </table>
            </div>
            """
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                weight=1,
                popup=folium.Popup(popup_html, max_width=240),
                tooltip=callsign,
            ).add_to(m)

        st_folium(m, width="100%", height=480, returned_objects=[])

        # Leyenda
        st.markdown("""
        <div class="map-legend">
          <span class="legend-item">
            <span class="legend-dot" style="background:#ef4444"></span> &gt; 30 000 ft
          </span>
          <span class="legend-item">
            <span class="legend-dot" style="background:#f97316"></span> 20–30 000 ft
          </span>
          <span class="legend-item">
            <span class="legend-dot" style="background:#22c55e"></span> 10–20 000 ft
          </span>
          <span class="legend-item">
            <span class="legend-dot" style="background:#3b82f6"></span> &lt; 10 000 ft
          </span>
          <span class="legend-item">
            <span class="legend-dot" style="background:#64748b"></span> Sin datos
          </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="custom-info">
            No hay coordenadas validas en los registros recibidos.
        </div>
        """, unsafe_allow_html=True)

# ── Tabla ─────────────────────────────────────────────────────────────────────
with col_table:
    st.markdown('<div class="section-title">Registros de vuelo</div>',
                unsafe_allow_html=True)

    preferred = ["callsign", "icao24", "origin_country",
                 "altitude", "velocity", "heading",
                 "latitude", "longitude", "on_ground", "timestamp"]
    available = [c for c in preferred if c in df.columns]
    table_df  = df[available].copy()

    if "timestamp" in table_df.columns:
        table_df["timestamp"] = (
            table_df["timestamp"]
            .dt.strftime("%H:%M:%S")
            .fillna("—")
        )

    col_cfg = {}
    cfg_map = {
        "latitude":  ("Latitud",    "%.4f"),
        "longitude": ("Longitud",   "%.4f"),
        "altitude":  ("Alt (ft)",   "%.0f"),
        "velocity":  ("Vel (kn)",   "%.0f"),
        "heading":   ("Rumbo",      "%.0f"),
    }
    for field, (label, fmt) in cfg_map.items():
        if field in table_df.columns:
            col_cfg[field] = st.column_config.NumberColumn(label, format=fmt)

    if "on_ground" in table_df.columns:
        col_cfg["on_ground"] = st.column_config.CheckboxColumn("En tierra")

    st.dataframe(
        table_df,
        use_container_width=True,
        height=530,
        column_config=col_cfg,
        hide_index=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Pie
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""
    <p style="font-size:0.75rem;color:#475569;margin:0">
        Datos en tiempo real con cache de {refresh_ttl} segundos &mdash;
        Fuente: <strong>OpenSky Network</strong> via FlightTracker API &mdash;
        {now_str}
    </p>
    """,
    unsafe_allow_html=True,
)
