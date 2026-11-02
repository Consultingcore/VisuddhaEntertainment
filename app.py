from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# Configuración general
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Cobranza de Eventos Musicales",
    page_icon="🎶",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "data" / "datos.csv"
PALETA = px.colors.qualitative.Bold
COLORES_ESTATUS = {
    "Pagada": "#2ca02c",
    "Parcial": "#ffbf00",
    "Pendiente": "#1f77b4",
    "Vencida": "#d62728",
}


@st.cache_data
def cargar_datos(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    for col in ["fecha_emision", "fecha_evento", "fecha_vencimiento", "fecha_ultimo_pago"]:
        df[col] = pd.to_datetime(df[col])
    return df


def mxn(valor: float) -> str:
    return f"${valor:,.0f}"


def estilo(fig, alto=430):
    """Estilo profesional común para todos los gráficos."""
    fig.update_layout(
        template="plotly_white",
        height=alto,
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(family="Arial", size=13),
        title=dict(font=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        hoverlabel=dict(font_size=13),
    )
    return fig


# ------------------------------------------------------------------
# Carga de datos
# ------------------------------------------------------------------
if not DATA_PATH.exists():
    st.error(f"No se encontró el archivo de datos en: {DATA_PATH}")
    st.stop()

df = cargar_datos(DATA_PATH)

# ------------------------------------------------------------------
# Título y subtítulo
# ------------------------------------------------------------------
st.title("🎶💍 Cobranza y Contratación Musical para Eventos 🎂👶")
st.subheader("🎻 Seguimiento de facturas, ingresos y cuentas por cobrar: bodas, cumpleaños y bautizos 💰")
st.divider()

# ------------------------------------------------------------------
# Filtros (barra lateral)
# ------------------------------------------------------------------
st.sidebar.header("🎛️ Filtros")

opc_evento = ["Todos"] + sorted(df["tipo_evento"].unique())
opc_servicio = ["Todos"] + sorted(df["servicio_contratado"].unique())
opc_estatus = ["Todos"] + sorted(df["estatus_pago"].unique())
opc_vendedor = ["Todos"] + sorted(df["vendedor"].unique())

sel_evento = st.sidebar.selectbox("🎉 Tipo de evento", opc_evento)
sel_servicio = st.sidebar.selectbox("🎤 Servicio contratado", opc_servicio)
sel_estatus = st.sidebar.selectbox("🧾 Estatus de pago", opc_estatus)
sel_vendedor = st.sidebar.selectbox("🧑‍💼 Vendedor", opc_vendedor)

st.sidebar.markdown("**Opciones rápidas**")
solo_saldo = st.sidebar.checkbox("💸 Solo facturas con saldo pendiente")
solo_recurrentes = st.sidebar.checkbox("🔁 Solo clientes recurrentes")
solo_cfdi = st.sidebar.checkbox("📄 Solo facturas con CFDI")

filtrado = df.copy()
if sel_evento != "Todos":
    filtrado = filtrado[filtrado["tipo_evento"] == sel_evento]
if sel_servicio != "Todos":
    filtrado = filtrado[filtrado["servicio_contratado"] == sel_servicio]
if sel_estatus != "Todos":
    filtrado = filtrado[filtrado["estatus_pago"] == sel_estatus]
if sel_vendedor != "Todos":
    filtrado = filtrado[filtrado["vendedor"] == sel_vendedor]
if solo_saldo:
    filtrado = filtrado[filtrado["saldo_pendiente_mxn"] > 0]
if solo_recurrentes:
    filtrado = filtrado[filtrado["cliente_recurrente"]]
if solo_cfdi:
    filtrado = filtrado[filtrado["requiere_cfdi"]]

st.sidebar.caption(f"📌 {len(filtrado)} de {len(df)} facturas coinciden con los filtros.")

# ------------------------------------------------------------------
# Vista previa del DataFrame
# ------------------------------------------------------------------
if st.checkbox("👀 Mostrar vista previa de los datos filtrados"):
    st.dataframe(filtrado.head(10), width="stretch", hide_index=True)

if filtrado.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados. Ajusta los filtros para continuar.")
    st.stop()

# ------------------------------------------------------------------
# KPIs
# ------------------------------------------------------------------
total_facturado = filtrado["monto_total_mxn"].sum()
total_cobrado = filtrado["monto_pagado_mxn"].sum()
total_saldo = filtrado["saldo_pendiente_mxn"].sum()
pct_cobrado = total_cobrado / total_facturado * 100 if total_facturado else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("🧾 Facturado", mxn(total_facturado), f"{len(filtrado)} facturas", delta_color="off")
k2.metric("✅ Cobrado", mxn(total_cobrado), f"{pct_cobrado:.1f}% del total", delta_color="off")
k3.metric("⏳ Por cobrar", mxn(total_saldo))
k4.metric("🚨 Facturas vencidas", int((filtrado["estatus_pago"] == "Vencida").sum()))

st.write("")

# ------------------------------------------------------------------
# Gráfico 1 (barras) y Gráfico 2 (donut)
# ------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    barras = (
        filtrado.groupby(["servicio_contratado", "tipo_evento"], as_index=False)["monto_total_mxn"].sum()
    )
    orden = (
        barras.groupby("servicio_contratado")["monto_total_mxn"].sum().sort_values().index.tolist()
    )
    fig1 = px.bar(
        barras,
        x="monto_total_mxn",
        y="servicio_contratado",
        color="tipo_evento",
        orientation="h",
        category_orders={"servicio_contratado": orden},
        color_discrete_sequence=PALETA,
        labels={
            "monto_total_mxn": "Monto facturado (MXN)",
            "servicio_contratado": "Servicio",
            "tipo_evento": "Tipo de evento",
        },
        title="🎤 Ingresos facturados por servicio y tipo de evento",
    )
    fig1.update_traces(hovertemplate="<b>%{y}</b><br>%{x:$,.0f} MXN<extra></extra>")
    fig1.update_xaxes(tickprefix="$", separatethousands=True)
    st.plotly_chart(estilo(fig1), width="stretch")

with col2:
    dona = filtrado.groupby("estatus_pago", as_index=False)["monto_total_mxn"].sum()
    fig2 = px.pie(
        dona,
        names="estatus_pago",
        values="monto_total_mxn",
        hole=0.5,
        color="estatus_pago",
        color_discrete_map=COLORES_ESTATUS,
        title="🧾 Distribución del monto facturado por estatus de pago",
    )
    fig2.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>%{value:$,.0f} MXN<br>%{percent}<extra></extra>",
        pull=[0.03] * len(dona),
    )
    fig2.add_annotation(
        text=f"<b>{mxn(total_facturado)}</b><br>facturado",
        x=0.5, y=0.5, showarrow=False, font=dict(size=16),
    )
    st.plotly_chart(estilo(fig2), width="stretch")

# ------------------------------------------------------------------
# Gráfico 3 (histograma, ancho completo)
# ------------------------------------------------------------------
fig3 = px.histogram(
    filtrado,
    x="monto_total_mxn",
    color="estatus_pago",
    nbins=20,
    marginal="box",
    barmode="stack",
    color_discrete_map=COLORES_ESTATUS,
    labels={"monto_total_mxn": "Monto total de la factura (MXN)", "estatus_pago": "Estatus"},
    title="📊 Distribución del monto de las facturas",
)
fig3.update_traces(selector=dict(type="histogram"), hovertemplate="Rango: %{x}<br>Facturas: %{y}<extra></extra>")
fig3.update_xaxes(tickprefix="$", separatethousands=True)
fig3.update_yaxes(title_text="Número de facturas", row=1, col=1)
st.plotly_chart(estilo(fig3, alto=480), width="stretch")

st.caption("💡 Datos simulados con fines demostrativos · Pasa el cursor sobre los gráficos para ver detalles.")
