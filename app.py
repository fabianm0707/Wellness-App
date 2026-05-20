import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

SHEET_ID = "1vhcan1qZzY6jiW8yMTWyNAUtI8A-4FjWB5OGKE0piGk"
SHEET_GID = "1726128126"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

ALERT_THRESHOLD = 5.0

GREEN  = "#00ff87"
YELLOW = "#ffd700"
ORANGE = "#ff6b35"
RED    = "#ff4757"
CYAN   = "#00d4ff"
BG     = "#0a0e1a"
CARD   = "#131929"
CARD2  = "#1a2235"


def inject_css():
    st.markdown(f"""
    <style>
    /* ── Background ── */
    .stApp {{
        background: {BG};
    }}
    section[data-testid="stSidebar"] {{
        background: {CARD};
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: {CARD};
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        color: #8892a4;
        font-weight: 700;
        font-size: 14px;
        padding: 10px 24px;
        letter-spacing: 0.5px;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, #1e3a5f, #0d2137) !important;
        color: {CYAN} !important;
        border-bottom: 2px solid {CYAN} !important;
    }}

    /* ── Text ── */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {{
        color: white !important;
    }}
    p, label, .stSelectbox label, .stDateInput label {{
        color: #a0aec0 !important;
    }}

    /* ── Inputs ── */
    .stSelectbox > div > div,
    .stDateInput > div > div > input {{
        background: {CARD2} !important;
        color: white !important;
        border: 1px solid #2d3748 !important;
        border-radius: 8px !important;
    }}

    /* ── Divider ── */
    hr {{
        border-color: #2d3748 !important;
    }}

    /* ── Dataframe ── */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
    }}

    /* ── Expander ── */
    .streamlit-expanderHeader {{
        background: {CARD2} !important;
        color: white !important;
        border-radius: 8px !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def metric_card(label: str, value: str, color: str = CYAN, icon: str = ""):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{CARD},{CARD2});
                border-radius:14px;padding:22px 16px;
                border-left:4px solid {color};text-align:center;
                box-shadow:0 4px 20px rgba(0,0,0,0.4);margin:4px 0;">
        <div style="color:#6b7a99;font-size:11px;font-weight:700;
                    text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">
            {icon}&nbsp;{label}
        </div>
        <div style="color:white;font-size:30px;font-weight:900;
                    line-height:1;text-shadow:0 0 20px {color}44;">
            {value}
        </div>
    </div>""", unsafe_allow_html=True)


def badge(label: str, color: str) -> str:
    return (f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
            f'border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;">{label}</span>')


def dark_chart(fig, height: int = 340):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(19,25,41,0.6)",
        font=dict(color="#a0aec0", family="Inter, sans-serif"),
        height=height,
        margin=dict(t=40, b=20, l=10, r=10),
        title_font=dict(size=15, color="white"),
    )
    fig.update_xaxes(gridcolor="#2d3748", zeroline=False)
    fig.update_yaxes(gridcolor="#2d3748", zeroline=False)
    return fig


def wellness_color(score: float) -> str:
    if score <= 2:    return GREEN
    if score <= 3.5:  return YELLOW
    if score <= 5:    return ORANGE
    return RED


def wellness_label(score: float) -> str:
    if score <= 2:    return "Excelente"
    if score <= 3.5:  return "Bueno"
    if score <= 5:    return "Regular"
    return "Requiere Atención"


def readiness_label(score: float) -> str:
    if score <= 2.5:  return "Listo"
    if score <= 4:    return "Precaución"
    return "Necesita Descanso"


def readiness_color(score: float) -> str:
    if score <= 2.5:  return GREEN
    if score <= 4:    return YELLOW
    return RED


def consecutive_alert_days(player_df: pd.DataFrame, threshold: float = 5.0) -> int:
    daily = player_df.sort_values("date").groupby("date")["wellness"].mean()
    count = 0
    for val in reversed(daily.values):
        if val >= threshold:
            count += 1
        else:
            break
    return count


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()
    rename_map = {"Timestamp": "timestamp", "Fecha": "date", "Jugador": "player", "Wellness Score": "wellness"}
    for col in df.columns:
        s = col.strip().lower()
        if "fatiga" in s:          rename_map[col] = "fatigue"
        elif "doms" in s or "dolor" in s: rename_map[col] = "doms"
        elif "estr" in s:          rename_map[col] = "stress"
        elif "sue" in s:           rename_map[col] = "sleep"
    df = df.rename(columns=rename_map)
    df = df[[c for c in ["timestamp", "date", "player", "fatigue", "doms", "stress", "sleep", "wellness"] if c in df.columns]]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = df["timestamp"].dt.normalize()
    for col in ["fatigue", "doms", "stress", "sleep", "wellness"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["player", "timestamp"])
    df["player"] = df["player"].str.strip()
    return df


def compute_readiness(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["readiness"] = (df["fatigue"] + df["stress"] + df["sleep"]) / 3
    df["recovery"]  = (df["fatigue"] + df["doms"]) / 2
    return df


# ─────────────────────────────────────────────
def render_team_dashboard(df: pd.DataFrame):
    st.markdown("## 📊 Panel del Equipo")

    min_date  = df["date"].min().date()
    max_date  = df["date"].max().date()
    def_start = max(min_date, max_date - timedelta(days=30))

    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("Desde", value=def_start, min_value=min_date, max_value=max_date)
    with c2:
        end = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)

    filtered = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    if filtered.empty:
        st.warning("No hay datos para el rango seleccionado.")
        return

    avg_team      = filtered["wellness"].mean()
    alerts        = filtered[filtered["wellness"] >= ALERT_THRESHOLD]["player"].nunique()
    submissions   = len(filtered)
    players_today = filtered[filtered["date"].dt.date == max_date]["player"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    with k1: metric_card("Bienestar Promedio", f"{avg_team:.2f} / 7", wellness_color(avg_team), "💚")
    with k2: metric_card("Jugadores en Alerta", str(alerts), RED if alerts > 0 else GREEN, "🚨")
    with k3: metric_card("Registros en el Período", str(submissions), CYAN, "📋")
    with k4: metric_card("Jugadores Hoy", str(players_today), YELLOW, "👥")

    st.markdown("<br>", unsafe_allow_html=True)

    trend = filtered.groupby("date")["wellness"].mean().reset_index()
    fig = px.area(trend, x="date", y="wellness",
                  title="Bienestar Promedio del Equipo",
                  labels={"date": "Fecha", "wellness": "Puntuación"},
                  color_discrete_sequence=[CYAN])
    fig.add_hline(y=ALERT_THRESHOLD, line_dash="dash", line_color=RED,
                  annotation_text="Umbral de Alerta", annotation_font_color=RED)
    fig.update_layout(yaxis_range=[1, 7])
    st.plotly_chart(dark_chart(fig, 320), use_container_width=True)

    st.markdown("### Desglose por Métrica")
    mdf = filtered.groupby("date")[["fatigue", "doms", "stress", "sleep"]].mean().reset_index()
    mdf = mdf.melt(id_vars="date", var_name="Métrica", value_name="Valor")
    mdf["Métrica"] = mdf["Métrica"].map({"fatigue": "Fatiga", "doms": "DOMS", "stress": "Estrés", "sleep": "Sueño"})
    fig2 = px.line(mdf, x="date", y="Valor", color="Métrica", markers=True,
                   labels={"date": "Fecha"},
                   color_discrete_sequence=[RED, ORANGE, YELLOW, CYAN])
    fig2.update_layout(yaxis_range=[1, 7])
    st.plotly_chart(dark_chart(fig2, 300), use_container_width=True)

    st.markdown("### Bienestar por Jugador")
    pavg = filtered.groupby("player")["wellness"].mean().sort_values(ascending=False).reset_index()
    fig3 = px.bar(pavg, x="wellness", y="player", orientation="h",
                  color="wellness",
                  color_continuous_scale=[[0, GREEN], [0.4, YELLOW], [0.7, ORANGE], [1, RED]],
                  range_color=[1, 7],
                  labels={"wellness": "Puntuación", "player": "Jugador"})
    fig3.update_layout(height=max(420, len(pavg) * 22), coloraxis_showscale=False,
                       yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(dark_chart(fig3, max(420, len(pavg) * 22)), use_container_width=True)

    if alerts > 0:
        st.markdown(f"### 🚨 Jugadores en Alerta &nbsp;_(puntuación ≥ {ALERT_THRESHOLD})_")
        adf = (filtered[filtered["wellness"] >= ALERT_THRESHOLD]
               .groupby("player")
               .agg(avg=("wellness", "mean"), last=("date", "max"), n=("wellness", "count"))
               .reset_index().sort_values("avg", ascending=False))
        adf.columns = ["Jugador", "Bienestar Promedio", "Último Registro", "Registros"]
        adf["Bienestar Promedio"] = adf["Bienestar Promedio"].round(2)
        st.dataframe(adf, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
def render_player_profile(df: pd.DataFrame):
    st.markdown("## 👤 Perfil del Jugador")

    players  = sorted(df["player"].dropna().unique())
    selected = st.selectbox("Selecciona un Jugador", players)
    pdf      = df[df["player"] == selected].sort_values("date")

    if pdf.empty:
        st.info("No hay datos para este jugador.")
        return

    last  = pdf.iloc[-1]
    score = last["wellness"]
    color = wellness_color(score)
    label = wellness_label(score)

    k1, k2, k3 = st.columns(3)
    with k1: metric_card("Última Puntuación", f"{score:.2f}", color, "🎯")
    with k2: metric_card("Estado", label, color, "📌")
    with k3: metric_card("Total de Registros", str(len(pdf)), CYAN, "📅")

    st.markdown("<br>", unsafe_allow_html=True)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Última Puntuación de Bienestar", "font": {"color": "white", "size": 14}},
        number={"font": {"color": color, "size": 48}},
        gauge={
            "axis": {"range": [1, 7], "tickcolor": "#6b7a99"},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": CARD2,
            "bordercolor": "#2d3748",
            "steps": [
                {"range": [1, 2],   "color": "#0d2e1a"},
                {"range": [2, 3.5], "color": "#2e2a0a"},
                {"range": [3.5, 5], "color": "#2e1a0a"},
                {"range": [5, 7],   "color": "#2e0a0a"},
            ],
            "threshold": {"line": {"color": RED, "width": 3}, "thickness": 0.8, "value": ALERT_THRESHOLD},
        },
    ))
    st.plotly_chart(dark_chart(fig_gauge, 280), use_container_width=True)

    fig_trend = px.line(pdf, x="date", y="wellness",
                        title=f"Tendencia de Bienestar — {selected}",
                        labels={"date": "Fecha", "wellness": "Puntuación"},
                        markers=True, color_discrete_sequence=[color])
    fig_trend.add_hline(y=ALERT_THRESHOLD, line_dash="dash", line_color=RED,
                        annotation_text="Umbral de Alerta", annotation_font_color=RED)
    fig_trend.update_traces(line=dict(width=3), marker=dict(size=8))
    fig_trend.update_layout(yaxis_range=[1, 7])
    st.plotly_chart(dark_chart(fig_trend, 300), use_container_width=True)

    st.markdown("### Último Registro — Detalle")
    cats   = ["Fatiga", "DOMS", "Estrés", "Sueño"]
    vals   = [last.get("fatigue", 0), last.get("doms", 0), last.get("stress", 0), last.get("sleep", 0)]
    fig_r  = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself", line_color=color, fillcolor=color, opacity=0.35,
        line=dict(width=2),
    ))
    fig_r.update_layout(polar=dict(
        bgcolor=CARD2,
        radialaxis=dict(visible=True, range=[1, 7], gridcolor="#2d3748", tickfont=dict(color="#6b7a99")),
        angularaxis=dict(gridcolor="#2d3748", tickfont=dict(color="white", size=13)),
    ), height=400, margin=dict(t=20, b=20))
    st.plotly_chart(dark_chart(fig_r, 400), use_container_width=True)

    with st.expander("Ver historial completo"):
        disp = pdf[["date", "fatigue", "doms", "stress", "sleep", "wellness"]].copy()
        disp.columns = ["Fecha", "Fatiga", "DOMS", "Estrés", "Sueño", "Bienestar"]
        disp["Fecha"] = disp["Fecha"].dt.strftime("%Y-%m-%d")
        st.dataframe(disp.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
def render_recovery_readiness(df: pd.DataFrame):
    st.markdown("## 🔋 Recuperación y Preparación")

    df       = compute_readiness(df)
    max_date = df["date"].max().date()

    st.markdown("### Estado del Equipo Hoy")
    today_df = df[df["date"].dt.date == max_date].copy()

    if today_df.empty:
        st.info(f"No hay registros para hoy ({max_date}).")
    else:
        ts = (today_df.groupby("player")
              .agg(readiness=("readiness","mean"), recovery=("recovery","mean"), wellness=("wellness","mean"))
              .reset_index())
        ts["Estado"] = ts["readiness"].apply(readiness_label)

        ready   = (ts["readiness"] <= 2.5).sum()
        caution = ((ts["readiness"] > 2.5) & (ts["readiness"] <= 4)).sum()
        rest    = (ts["readiness"] > 4).sum()

        c1, c2, c3 = st.columns(3)
        with c1: metric_card("Listos para Entrenar", str(ready), GREEN, "✅")
        with c2: metric_card("Precaución", str(caution), YELLOW, "⚠️")
        with c3: metric_card("Necesitan Descanso", str(rest), RED, "🛑")

        st.markdown("<br>", unsafe_allow_html=True)

        fig_d = px.pie(
            names=["Listo", "Precaución", "Necesita Descanso"],
            values=[ready, caution, rest],
            color=["Listo", "Precaución", "Necesita Descanso"],
            color_discrete_map={"Listo": GREEN, "Precaución": YELLOW, "Necesita Descanso": RED},
            hole=0.55,
            title="Distribución de Preparación — Hoy",
        )
        fig_d.update_traces(textfont=dict(color="white", size=13))
        st.plotly_chart(dark_chart(fig_d, 300), use_container_width=True)

        ts = ts.sort_values("readiness", ascending=False)
        for col in ["readiness", "recovery", "wellness"]:
            ts[col] = ts[col].round(2)
        ts.columns = ["Jugador", "Preparación", "Recuperación", "Bienestar", "Estado"]
        st.dataframe(ts, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("### 🗓️ Mapa de Preparación — Últimos 21 Días")
    cutoff   = pd.Timestamp(max_date) - timedelta(days=21)
    hdf      = df[df["date"] >= cutoff].copy()
    hdf["date_str"] = hdf["date"].dt.strftime("%m/%d")
    pivot    = hdf.groupby(["player", "date_str"])["readiness"].mean().reset_index()
    pw       = pivot.pivot(index="player", columns="date_str", values="readiness")
    fig_h    = px.imshow(pw,
        color_continuous_scale=[[0, GREEN], [0.4, YELLOW], [0.7, ORANGE], [1, RED]],
        range_color=[1, 7],
        labels={"color": "Preparación", "x": "Fecha", "y": "Jugador"},
        aspect="auto")
    fig_h.update_layout(coloraxis_colorbar=dict(title="Score", tickfont=dict(color="white")))
    st.plotly_chart(dark_chart(fig_h, max(420, len(pw) * 24)), use_container_width=True)

    st.divider()

    st.markdown("### ⚡ Días Consecutivos en Alerta")
    consec = [{"Jugador": p, "Días Consecutivos": consecutive_alert_days(df[df["player"] == p])}
              for p in df["player"].unique()]
    consec = [r for r in consec if r["Días Consecutivos"] > 0]

    if consec:
        cdf = pd.DataFrame(consec).sort_values("Días Consecutivos", ascending=False)
        fig_c = px.bar(cdf, x="Días Consecutivos", y="Jugador", orientation="h",
                       color="Días Consecutivos",
                       color_continuous_scale=[[0, YELLOW], [0.5, ORANGE], [1, RED]],
                       title="Jugadores con Días Consecutivos de Bienestar Bajo")
        fig_c.update_layout(height=max(300, len(cdf) * 30), coloraxis_showscale=False,
                             yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(dark_chart(fig_c), use_container_width=True)
    else:
        st.success("Ningún jugador tiene días consecutivos en alerta actualmente.")

    st.divider()

    st.markdown("### 📈 Tendencia de Recuperación del Equipo")
    r_min         = df["date"].min().date()
    r_def_start   = max(r_min, max_date - timedelta(days=30))
    rc1, rc2      = st.columns(2)
    with rc1:
        r_start = st.date_input("Desde", value=r_def_start, min_value=r_min, max_value=max_date, key="r_start")
    with rc2:
        r_end   = st.date_input("Hasta", value=max_date,    min_value=r_min, max_value=max_date, key="r_end")

    rdf = df[(df["date"].dt.date >= r_start) & (df["date"].dt.date <= r_end)]
    if not rdf.empty:
        rt  = rdf.groupby("date")[["readiness", "recovery"]].mean().reset_index()
        rt  = rt.melt(id_vars="date", var_name="Métrica", value_name="Puntuación")
        rt["Métrica"] = rt["Métrica"].map({"readiness": "Preparación", "recovery": "Recuperación"})
        fig_r = px.line(rt, x="date", y="Puntuación", color="Métrica", markers=True,
                        labels={"date": "Fecha"},
                        title="Preparación vs Recuperación del Equipo",
                        color_discrete_sequence=[CYAN, GREEN])
        fig_r.add_hline(y=4, line_dash="dash", line_color=YELLOW,
                        annotation_text="Umbral de Precaución", annotation_font_color=YELLOW)
        fig_r.update_traces(line=dict(width=2.5), marker=dict(size=7))
        fig_r.update_layout(yaxis_range=[1, 7])
        st.plotly_chart(dark_chart(fig_r, 320), use_container_width=True)

    st.divider()

    st.markdown("### 😴 Impacto del Sueño en la Preparación")
    fig_s = px.scatter(df, x="sleep", y="readiness", color="player",
                       labels={"sleep": "Calidad del Sueño", "readiness": "Preparación", "player": "Jugador"},
                       title="Calidad del Sueño vs Preparación", opacity=0.7)
    fig_s.update_traces(marker=dict(size=8))
    fig_s.update_layout(showlegend=False)
    st.plotly_chart(dark_chart(fig_s, 380), use_container_width=True)


# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Panel de Bienestar",
        page_icon="⚽",
        layout="wide",
    )
    inject_css()

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d2137 0%,#1a3a5c 50%,#0d2137 100%);
                border-radius:16px;padding:28px 36px;margin-bottom:24px;
                border:1px solid #1e4976;box-shadow:0 8px 32px rgba(0,212,255,0.1);">
        <div style="display:flex;align-items:center;gap:20px;">
            <img src="https://tmssl.akamaized.net//images/wappen/head/70466.png?lm=1735917818"
                 style="height:80px;width:auto;filter:drop-shadow(0 0 12px rgba(0,212,255,0.4));">
            <div>
                <div style="color:white;font-size:28px;font-weight:900;letter-spacing:1px;">
                    Leones del Norte FC
                </div>
                <div style="color:#00d4ff;font-size:13px;font-weight:600;letter-spacing:2px;margin-top:4px;">
                    PANEL DE BIENESTAR · RECUPERACIÓN · PREPARACIÓN
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 Panel del Equipo", "👤 Perfil del Jugador", "🔋 Recuperación y Preparación"])

    with tab1:
        try:
            render_team_dashboard(load_data())
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")

    with tab2:
        try:
            render_player_profile(load_data())
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")

    with tab3:
        try:
            render_recovery_readiness(load_data())
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")


if __name__ == "__main__":
    main()
