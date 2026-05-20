import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

SHEET_ID = "1vhcan1qZzY6jiW8yMTWyNAUtI8A-4FjWB5OGKE0piGk"
SHEET_GID = "1726128126"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

ALERT_THRESHOLD = 5.0


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()

    rename_map = {
        "Timestamp": "timestamp",
        "Fecha": "date",
        "Jugador": "player",
        "Wellness Score": "wellness",
    }
    for col in df.columns:
        stripped = col.strip()
        if "fatiga" in stripped.lower():
            rename_map[col] = "fatigue"
        elif "DOMS" in stripped or "dolor" in stripped.lower():
            rename_map[col] = "doms"
        elif "estr" in stripped.lower():
            rename_map[col] = "stress"
        elif "sue" in stripped.lower():
            rename_map[col] = "sleep"

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


def wellness_color(score: float) -> str:
    if score <= 2:
        return "#2ecc71"
    elif score <= 3.5:
        return "#f1c40f"
    elif score <= 5:
        return "#e67e22"
    return "#e74c3c"


def wellness_label(score: float) -> str:
    if score <= 2:
        return "Excelente"
    elif score <= 3.5:
        return "Bueno"
    elif score <= 5:
        return "Regular"
    return "Requiere Atención"


def render_team_dashboard(df: pd.DataFrame):
    st.header("Panel del Equipo")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    default_start = max(min_date, max_date - timedelta(days=30))

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Desde", value=default_start, min_value=min_date, max_value=max_date)
    with col2:
        end = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)

    mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
    filtered = df[mask]

    if filtered.empty:
        st.warning("No hay datos disponibles para el rango de fechas seleccionado.")
        return

    # KPI row
    avg_team = filtered["wellness"].mean()
    alerts = filtered[filtered["wellness"] >= ALERT_THRESHOLD]["player"].nunique()
    submissions = len(filtered)
    players_today = filtered[filtered["date"].dt.date == max_date]["player"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Bienestar Promedio", f"{avg_team:.2f} / 7")
    k2.metric("Jugadores en Alerta", alerts)
    k3.metric("Registros en el período", submissions)
    k4.metric("Jugadores hoy", players_today)

    st.divider()

    # Team trend over time
    trend = filtered.groupby("date")["wellness"].mean().reset_index()
    fig_trend = px.line(
        trend, x="date", y="wellness",
        title="Bienestar Promedio del Equipo",
        labels={"date": "Fecha", "wellness": "Puntuación de Bienestar"},
        markers=True,
    )
    fig_trend.add_hline(y=ALERT_THRESHOLD, line_dash="dash", line_color="red",
                        annotation_text="Umbral de Alerta")
    fig_trend.update_layout(yaxis_range=[1, 7], height=320)
    st.plotly_chart(fig_trend, use_container_width=True)

    # Metric breakdown over time
    st.subheader("Desglose por Métrica")
    metrics_df = filtered.groupby("date")[["fatigue", "doms", "stress", "sleep"]].mean().reset_index()
    metrics_melted = metrics_df.melt(id_vars="date", var_name="Métrica", value_name="Valor")
    label_map = {"fatigue": "Fatiga", "doms": "DOMS", "stress": "Estrés", "sleep": "Sueño"}
    metrics_melted["Métrica"] = metrics_melted["Métrica"].map(label_map)
    fig_metrics = px.line(metrics_melted, x="date", y="Valor", color="Métrica", markers=True,
                          labels={"date": "Fecha", "Valor": "Puntuación"})
    fig_metrics.update_layout(yaxis_range=[1, 7], height=300)
    st.plotly_chart(fig_metrics, use_container_width=True)

    # Player averages bar chart
    st.subheader("Bienestar por Jugador")
    player_avg = filtered.groupby("player")["wellness"].mean().sort_values(ascending=False).reset_index()
    player_avg["color"] = player_avg["wellness"].apply(wellness_color)
    fig_players = px.bar(
        player_avg, x="wellness", y="player", orientation="h",
        color="wellness", color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        range_color=[1, 7],
        labels={"wellness": "Puntuación de Bienestar", "player": "Jugador"},
    )
    fig_players.update_layout(height=max(400, len(player_avg) * 20), coloraxis_showscale=False,
                               yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_players, use_container_width=True)

    # Alerts table
    if alerts > 0:
        st.subheader(f"Jugadores en Alerta (puntuación ≥ {ALERT_THRESHOLD})")
        alert_df = (
            filtered[filtered["wellness"] >= ALERT_THRESHOLD]
            .groupby("player")
            .agg(avg_wellness=("wellness", "mean"), last_date=("date", "max"), entries=("wellness", "count"))
            .reset_index()
            .sort_values("avg_wellness", ascending=False)
        )
        alert_df.columns = ["Jugador", "Bienestar Promedio", "Último Registro", "Registros"]
        alert_df["Bienestar Promedio"] = alert_df["Bienestar Promedio"].round(2)
        st.dataframe(alert_df, use_container_width=True, hide_index=True)


def render_player_profile(df: pd.DataFrame):
    st.header("Perfil del Jugador")

    players = sorted(df["player"].dropna().unique())
    selected = st.selectbox("Selecciona un Jugador", players)

    player_df = df[df["player"] == selected].sort_values("date")
    if player_df.empty:
        st.info("No hay datos disponibles para este jugador.")
        return

    last = player_df.iloc[-1]
    score = last["wellness"]
    color = wellness_color(score)
    label = wellness_label(score)

    col1, col2, col3 = st.columns(3)
    col1.metric("Última Puntuación", f"{score:.2f}")
    col2.metric("Estado", label)
    col3.metric("Total de Registros", len(player_df))

    # Gauge
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Última Puntuación de Bienestar"},
        gauge={
            "axis": {"range": [1, 7]},
            "bar": {"color": color},
            "steps": [
                {"range": [1, 2], "color": "#d5f5e3"},
                {"range": [2, 3.5], "color": "#fef9e7"},
                {"range": [3.5, 5], "color": "#fdebd0"},
                {"range": [5, 7], "color": "#fadbd8"},
            ],
        },
    ))
    fig_gauge.update_layout(height=250, margin=dict(t=30, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Trend line
    fig_trend = px.line(
        player_df, x="date", y="wellness",
        title=f"Tendencia de Bienestar — {selected}",
        labels={"date": "Fecha", "wellness": "Puntuación"},
        markers=True,
    )
    fig_trend.add_hline(y=ALERT_THRESHOLD, line_dash="dash", line_color="red",
                        annotation_text="Umbral de Alerta")
    fig_trend.update_layout(yaxis_range=[1, 7], height=300)
    st.plotly_chart(fig_trend, use_container_width=True)

    # Radar of last entry
    st.subheader("Último Registro — Detalle")
    categories = ["Fatiga", "DOMS", "Estrés", "Sueño"]
    values = [last.get("fatigue", 0), last.get("doms", 0), last.get("stress", 0), last.get("sleep", 0)]

    fig_radar = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        line_color=color,
        fillcolor=color,
        opacity=0.4,
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[1, 7])),
        height=380,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # History table
    with st.expander("Ver historial completo"):
        display = player_df[["date", "fatigue", "doms", "stress", "sleep", "wellness"]].copy()
        display.columns = ["Fecha", "Fatiga", "DOMS", "Estrés", "Sueño", "Bienestar"]
        display["Fecha"] = display["Fecha"].dt.strftime("%Y-%m-%d")
        st.dataframe(display.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)


def compute_readiness(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["readiness"] = (df["fatigue"] + df["stress"] + df["sleep"]) / 3
    df["recovery"] = (df["fatigue"] + df["doms"]) / 2
    return df


def readiness_label(score: float) -> str:
    if score <= 2.5:
        return "Listo"
    elif score <= 4:
        return "Precaución"
    return "Necesita Descanso"


def readiness_color(score: float) -> str:
    if score <= 2.5:
        return "#2ecc71"
    elif score <= 4:
        return "#f1c40f"
    return "#e74c3c"


def consecutive_alert_days(player_df: pd.DataFrame, threshold: float = 5.0) -> int:
    daily = player_df.sort_values("date").groupby("date")["wellness"].mean()
    count = 0
    for val in reversed(daily.values):
        if val >= threshold:
            count += 1
        else:
            break
    return count


def render_recovery_readiness(df: pd.DataFrame):
    st.header("Recuperación y Preparación")

    df = compute_readiness(df)
    max_date = df["date"].max().date()

    # --- Today's readiness board ---
    st.subheader("Estado del Equipo Hoy")
    today_df = df[df["date"].dt.date == max_date].copy()

    if today_df.empty:
        st.info(f"No hay registros para hoy ({max_date}).")
    else:
        today_summary = (
            today_df.groupby("player")
            .agg(readiness=("readiness", "mean"), recovery=("recovery", "mean"), wellness=("wellness", "mean"))
            .reset_index()
        )
        today_summary["Estado"] = today_summary["readiness"].apply(readiness_label)

        ready = (today_summary["readiness"] <= 2.5).sum()
        caution = ((today_summary["readiness"] > 2.5) & (today_summary["readiness"] <= 4)).sum()
        rest = (today_summary["readiness"] > 4).sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Listos para entrenar", ready)
        c2.metric("Precaución", caution)
        c3.metric("Necesitan descanso", rest)

        fig_donut = px.pie(
            names=["Listo", "Precaución", "Necesita Descanso"],
            values=[ready, caution, rest],
            color=["Listo", "Precaución", "Necesita Descanso"],
            color_discrete_map={"Listo": "#2ecc71", "Precaución": "#f1c40f", "Necesita Descanso": "#e74c3c"},
            hole=0.5,
            title="Distribución de Preparación — Hoy",
        )
        fig_donut.update_layout(height=300)
        st.plotly_chart(fig_donut, use_container_width=True)

        today_summary = today_summary.sort_values("readiness", ascending=False)
        today_summary["readiness"] = today_summary["readiness"].round(2)
        today_summary["recovery"] = today_summary["recovery"].round(2)
        today_summary["wellness"] = today_summary["wellness"].round(2)
        today_summary.columns = ["Jugador", "Preparación", "Recuperación", "Bienestar", "Estado"]
        st.dataframe(today_summary, use_container_width=True, hide_index=True)

    st.divider()

    # --- Readiness heatmap (last 21 days) ---
    st.subheader("Mapa de Preparación — Últimos 21 Días")
    cutoff = pd.Timestamp(max_date) - timedelta(days=21)
    heatmap_df = df[df["date"] >= cutoff].copy()
    heatmap_df["date_str"] = heatmap_df["date"].dt.strftime("%m/%d")
    pivot = heatmap_df.groupby(["player", "date_str"])["readiness"].mean().reset_index()
    pivot_wide = pivot.pivot(index="player", columns="date_str", values="readiness")

    fig_heat = px.imshow(
        pivot_wide,
        color_continuous_scale=["#2ecc71", "#f1c40f", "#e74c3c"],
        range_color=[1, 7],
        labels={"color": "Preparación", "x": "Fecha", "y": "Jugador"},
        aspect="auto",
    )
    fig_heat.update_layout(height=max(400, len(pivot_wide) * 22), coloraxis_colorbar_title="Score")
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # --- Consecutive alert days ---
    st.subheader("Días Consecutivos en Alerta")
    players = df["player"].unique()
    consec_data = []
    for p in players:
        pdf = df[df["player"] == p]
        days = consecutive_alert_days(pdf)
        if days > 0:
            consec_data.append({"Jugador": p, "Días Consecutivos": days})

    if consec_data:
        consec_df = pd.DataFrame(consec_data).sort_values("Días Consecutivos", ascending=False)
        fig_consec = px.bar(
            consec_df, x="Días Consecutivos", y="Jugador", orientation="h",
            color="Días Consecutivos",
            color_continuous_scale=["#f1c40f", "#e67e22", "#e74c3c"],
            title="Jugadores con Días Consecutivos de Bienestar Bajo",
        )
        fig_consec.update_layout(height=max(300, len(consec_df) * 28), coloraxis_showscale=False,
                                  yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_consec, use_container_width=True)
    else:
        st.success("Ningún jugador tiene días consecutivos de alerta actualmente.")

    st.divider()

    # --- Recovery trend over time ---
    st.subheader("Tendencia de Recuperación del Equipo")
    r_min = df["date"].min().date()
    r_default_start = max(r_min, max_date - timedelta(days=30))

    col1, col2 = st.columns(2)
    with col1:
        r_start = st.date_input("Desde", value=r_default_start,
                                 min_value=r_min, max_value=max_date, key="r_start")
    with col2:
        r_end = st.date_input("Hasta", value=max_date,
                               min_value=r_min, max_value=max_date, key="r_end")

    rmask = (df["date"].dt.date >= r_start) & (df["date"].dt.date <= r_end)
    rdf = df[rmask]

    if not rdf.empty:
        rec_trend = rdf.groupby("date")[["readiness", "recovery"]].mean().reset_index()
        rec_melted = rec_trend.melt(id_vars="date", var_name="Métrica", value_name="Puntuación")
        rec_melted["Métrica"] = rec_melted["Métrica"].map({"readiness": "Preparación", "recovery": "Recuperación"})
        fig_rec = px.line(rec_melted, x="date", y="Puntuación", color="Métrica", markers=True,
                          labels={"date": "Fecha"},
                          title="Preparación vs Recuperación del Equipo")
        fig_rec.add_hline(y=4, line_dash="dash", line_color="orange", annotation_text="Umbral de Precaución")
        fig_rec.update_layout(yaxis_range=[1, 7], height=320)
        st.plotly_chart(fig_rec, use_container_width=True)

    st.divider()

    # --- Sleep vs readiness scatter ---
    st.subheader("Impacto del Sueño en la Preparación")
    fig_scatter = px.scatter(
        df, x="sleep", y="readiness", color="player",
        labels={"sleep": "Calidad del Sueño", "readiness": "Preparación", "player": "Jugador"},
        title="Calidad del Sueño vs Preparación",
        opacity=0.6,
    )
    fig_scatter.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig_scatter, use_container_width=True)


def main():
    st.set_page_config(
        page_title="Panel de Bienestar del Jugador",
        page_icon="⚽",
        layout="wide",
    )
    st.title("⚽ Panel de Bienestar del Jugador")

    tab1, tab2, tab3 = st.tabs(["Panel del Equipo", "Perfil del Jugador", "Recuperación y Preparación"])

    with tab1:
        try:
            df = load_data()
            render_team_dashboard(df)
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")

    with tab2:
        try:
            df = load_data()
            render_player_profile(df)
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")

    with tab3:
        try:
            df = load_data()
            render_recovery_readiness(df)
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")


if __name__ == "__main__":
    main()
