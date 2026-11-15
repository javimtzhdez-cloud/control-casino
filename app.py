import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

ARCHIVO_EVENTOS = "eventos_casinos.csv"
ARCHIVO_PERSONAL = "personal_casinos.csv"
ARCHIVO_PAGOS = "pagos_casinos.csv"

st.set_page_config(page_title="Control de Casinos, Pagos y Sobres", page_icon="🎰", layout="wide")

st.title("🎰 Control Inteligente, Calendario, Pagos y Sobres - Casinos")
st.markdown("Gestión automatizada de personal, eventos, finanzas y control de sobres con generación de etiquetas PDF listas para imprimir.")

# Inicializar personal si no existe
if not os.path.exists(ARCHIVO_PERSONAL):
    df_personal_inicial = pd.DataFrame([
        {"Nombre": "Juan Pérez", "Puesto": "Mesero", "Casino_Habitual": "Casino 1"},
        {"Nombre": "María Gómez", "Puesto": "Barra", "Casino_Habitual": "Casino 1"},
        {"Nombre": "Carlos Ruiz", "Puesto": "Garrotero", "Casino_Habitual": "Casino 1"},
        {"Nombre": "Ana López", "Puesto": "Mesero", "Casino_Habitual": "Casino 2"},
        {"Nombre": "Luis Torres", "Puesto": "Barra", "Casino_Habitual": "Casino 2"},
        {"Nombre": "Sofía Martínez", "Puesto": "Garrotero", "Casino_Habitual": "Casino 2"}
    ])
    df_personal_inicial.to_csv(ARCHIVO_PERSONAL, index=False)

df_personal = pd.read_csv(ARCHIVO_PERSONAL)

# Cargar eventos
if os.path.exists(ARCHIVO_EVENTOS):
    df_eventos = pd.read_csv(ARCHIVO_EVENTOS)
    if "Pago_Monto" not in df_eventos.columns:
        df_eventos["Pago_Monto"] = 500.0
        df_eventos.to_csv(ARCHIVO_EVENTOS, index=False)
else:
    df_eventos = pd.DataFrame(columns=["Fecha", "Casino_Evento", "Nombre_Evento", "Tipo_Evento", "Personal", "Puesto", "Pago_Monto"])

# Cargar pagos generales
if os.path.exists(ARCHIVO_PAGOS):
    df_pagos = pd.read_csv(ARCHIVO_PAGOS)
else:
    df_pagos = pd.DataFrame(columns=["Fecha", "Casino", "Concepto", "Monto", "Estatus", "Metodo"])

def seleccionar_personal_automatico(fecha_str, casino_evento, puesto_requerido, df_p, df_ev):
    candidatos = df_p[df_p["Puesto"].str.lower() == puesto_requerido.lower()].copy()
    if candidatos.empty:
        return None, "No hay personal registrado con ese puesto."

    if not df_ev.empty:
        ocupados_en_fecha = df_ev[df_ev["Fecha"] == fecha_str]["Personal"].tolist()
        candidatos = candidatos[~candidatos["Nombre"].isin(ocupados_en_fecha)]
    
    if candidatos.empty:
        return None, "Todo el personal de este puesto ya está asignado en esta fecha."

    if casino_evento == "Casino 3":
        if not df_ev.empty and "Casino_Evento" in df_ev.columns:
            historial_c3 = df_ev[df_ev["Casino_Evento"] == "Casino 3"]["Personal"].value_counts()
            candidatos["Conteo_C3"] = candidatos["Nombre"].map(historial_c3).fillna(0)
            candidatos = candidatos.sort_values(by="Conteo_C3", ascending=True)
        elegido = candidatos.iloc[0]["Nombre"]
        return elegido, "Asignado a Casino 3 (Rotación)."
    else:
        habituales = candidatos[candidatos["Casino_Habitual"] == casino_evento]
        if not habituales.empty:
            elegido = habituales.iloc[0]["Nombre"]
            return elegido, f"Asignado a su casino base ({casino_evento})."
        else:
            elegido = candidatos.iloc[0]["Nombre"]
            return elegido, "Asignado por rotación (su base está ocupada)."

def generar_pdf_etiquetas(df_filtrado, fecha_pago):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('LabelTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1f2937'))
    style_body = ParagraphStyle('LabelBody', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#374151'), leading=11)
    style_money = ParagraphStyle('LabelMoney', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#047857'), leading=13)

    elements = []
    table_data = []
    row = []

    for _, row_data in df_filtrado.iterrows():
        trabajador = row_data["Personal"]
        futuros = df_eventos[(df_eventos["Personal"] == trabajador) & (df_eventos["Fecha"] > fecha_pago)]
        proximo_evento = "Sin asignar"
        if not futuros.empty:
            futuros = futuros.sort_values(by="Fecha")
            prox = futuros.iloc[0]
            proximo_evento = f"{prox['Fecha']} | {prox['Casino_Evento']} ({prox['Nombre_Evento']})"

        monto_val = row_data.get('Pago_Monto', 0)
        content = [
            Paragraph(f"<b>{row_data['Personal']}</b> ({row_data['Puesto']})", style_title),
            Spacer(1, 3),
            Paragraph(f"<b>PAGA:</b> ${monto_val:,.2f} MXN | Trab: {row_data['Casino_Evento']} ({row_data['Nombre_Evento']})", style_money),
            Spacer(1, 3),
            Paragraph(f"<b>Próxima:</b> {proximo_evento}", style_body)
        ]
        
        label_table = Table([[content]], colWidths=[270], rowHeights=[95])
        label_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#9ca3af')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        
        row.append(label_table)
        if len(row) == 2:
            table_data.append(row)
            row = []

    if row:
        row.append('')
        table_data.append(row)

    if table_data:
        main_table = Table(table_data, colWidths=[278, 278])
        main_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(main_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 Registrar Evento", "📅 Calendario y Casinos", "✉️ Generador de Etiquetas / Sobres", "💰 Control de Pagos", "👥 Directorio Personal"])

with tab1:
    st.subheader("Registrar Evento y Asignación de Personal")
    
    with st.form("form_auto_evento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha del Evento", value=datetime.now())
            casino_evento = st.selectbox("Casino del Evento", ["Casino 1", "Casino 2", "Casino 3"])
            nombre_evento = st.text_input("Nombre del Evento (ej. Boda de los 15s)")
        with col2:
            tipo_evento = st.selectbox("Tipo de Evento", [
                "Boda", "XV Años", "Cumpleaños / Festejo", "Evento Corporativo", "Comida / Cena Privada", "Otro"
            ])
            puesto_requerido = st.selectbox("Puesto que se necesita", ["Mesero", "Garrotero", "Barra", "Capitán"])
            pago_turno = st.number_input("Pago para este sobre ($ MXN)", min_value=0.0, value=500.0, step=50.0)
        
        submit_btn = st.form_submit_button("Asignar Automáticamente y Guardar")
        
        if submit_btn:
            if not nombre_evento.strip():
                st.error("Por favor ingresa el nombre del evento.")
            else:
                fecha_str = fecha.strftime("%Y-%m-%d")
                persona_elegida, mensaje_log = seleccionar_personal_automatico(
                    fecha_str, casino_evento, puesto_requerido, df_personal, df_eventos
                )
                
                if not persona_elegida:
                    st.error(f"No se pudo asignar: {mensaje_log}")
                else:
                    nuevo_registro = pd.DataFrame({
                        "Fecha": [fecha_str],
                        "Casino_Evento": [casino_evento],
                        "Nombre_Evento": [nombre_evento.strip()],
                        "Tipo_Evento": [tipo_evento],
                        "Personal": [persona_elegida],
                        "Puesto": [puesto_requerido],
                        "Pago_Monto": [pago_turno]
                    })
                    df_eventos = pd.concat([df_eventos, nuevo_registro], ignore_index=True)
                    df_eventos.to_csv(ARCHIVO_EVENTOS, index=False)
                    st.success(f"✅ ¡Asignación Exitosa! **{persona_elegida}** ({puesto_requerido}) fue asignado a **{casino_evento}** con un pago de ${pago_turno:,.2f}. ({mensaje_log})")
                    st.rerun()

with tab2:
    st.subheader("📅 Calendario y Desplegable por Casino")
    if df_eventos.empty:
        st.info("Aún no hay eventos registrados.")
    else:
        casino_seleccionado = st.selectbox("Selecciona un Casino para ver sus eventos:", ["Todos los Casinos", "Casino 1", "Casino 2", "Casino 3"])
        df_vista = df_eventos.copy()
        if casino_seleccionado != "Todos los Casinos":
            df_vista = df_vista[df_vista["Casino_Evento"] == casino_seleccionado]
            
        st.markdown(f"### Mostrando eventos para: **{casino_seleccionado}**")
        st.dataframe(df_vista.sort_values(by="Fecha"), use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗓️ Vista de Calendario (Próximos Eventos)")
        for index, row in df_eventos.sort_values(by="Fecha").iterrows():
            st.info(f"📅 **{row['Fecha']}** | 🎰 **{row['Casino_Evento']}** | 🎉 **{row['Nombre_Evento']}** ({row['Tipo_Evento']}) \n\n 👤 Asignado: **{row['Personal']}** (*{row['Puesto']}*) — Paga: **${row.get('Pago_Monto', 0):,.2f}**")

        if st.checkbox("Habilitar opción para eliminar un evento"):
            idx_del = st.number_input("Número de fila a eliminar del evento", min_value=0, max_value=max(0, len(df_eventos)-1), step=1)
            if st.button("Eliminar Evento Seleccionado"):
                df_eventos = df_eventos.drop(idx_del).reset_index(drop=True)
                df_eventos.to_csv(ARCHIVO_EVENTOS, index=False)
                st.warning("Evento eliminado.")
                st.rerun()

with tab3:
    st.subheader("✉️ Generador de Etiquetas / Sobres para Imprimir")
    st.markdown("Imprime **etiquetas adhesivas** (en hojas de calcomanía tamaño carta) para pegarlas en sobres económicos. Así te ahorras comprar sobres impresos caros o escribir a mano para los 40 trabajadores.")
    
    if df_eventos.empty:
        st.info("No hay eventos registrados todavía.")
    else:
        fechas_disponibles = sorted(df_eventos["Fecha"].unique(), reverse=True)
        fecha_pago_sel = st.selectbox("Selecciona la Fecha de Pago (Viernes de entrega):", fechas_disponibles)
        
        df_actuales = df_eventos[df_eventos["Fecha"] == fecha_pago_sel]
        
        filtro_sobre_casino = st.selectbox("Filtrar etiquetas por Casino:", ["Todos los Casinos", "Casino 1", "Casino 2", "Casino 3"], key="filtro_sobre")
        if filtro_sobre_casino != "Todos los Casinos":
            df_actuales = df_actuales[df_actuales["Casino_Evento"] == filtro_sobre_casino]
            
        st.markdown(f"### 📋 Vista previa de etiquetas para el {fecha_pago_sel} ({filtro_sobre_casino})")
        
        if not df_actuales.empty:
            pdf_bytes = generar_pdf_etiquetas(df_actuales, fecha_pago_sel)
            st.download_button(
                label="🖨️ Descargar PDF de Etiquetas (Listo para Imprimir)",
                data=pdf_bytes,
                file_name=f"etiquetas_sobres_{fecha_pago_sel}.pdf",
                mime="application/pdf",
                type="primary"
            )
        
        st.markdown("---")
        for _, row in df_actuales.iterrows():
            trabajador = row["Personal"]
            futuros = df_eventos[(df_eventos["Personal"] == trabajador) & (df_eventos["Fecha"] > fecha_pago_sel)]
            proximo_evento = "Sin evento asignado para la próxima semana"
            if not futuros.empty:
                futuros = futuros.sort_values(by="Fecha")
                prox = futuros.iloc[0]
                proximo_evento = f"📅 {prox['Fecha']} | 🎰 {prox['Casino_Evento']} | 🎉 {prox['Nombre_Evento']}"
            
            with st.container(border=True):
                col_s1, col_s2, col_s3 = st.columns([2, 2, 2])
                with col_s1:
                    st.markdown(f"### 👤 **{row['Personal']}**")
                    st.markdown(f"**Puesto:** {row['Puesto']}")
                    monto_val = row.get('Pago_Monto', 0)
                    st.markdown(f"💵 **Paga en sobre:** `$%0.2f MXN`" % monto_val)
                with col_s2:
                    st.markdown(f"📥 **Evento que ya trabajó:**")
                    st.markdown(f"• Casino: **{row['Casino_Evento']}**")
                    st.markdown(f"• Fecha: {row['Fecha']}")
                    st.markdown(f"• Evento: {row['Nombre_Evento']}")
                with col_s3:
                    st.markdown(f"🔜 **Próximo Evento (A la etiqueta):**")
                    st.markdown(f"*{proximo_evento}*")

with tab4:
    st.subheader("💰 Control de Pagos y Anticipos Generales")
    if df_pagos.empty:
        st.info("Aún no hay pagos registrados.")
    else:
        total_ingresos = df_pagos["Monto"].sum()
        st.metric(label="Total Registrado en Pagos", value=f"${total_ingresos:,.2f} MXN")
        st.dataframe(df_pagos, use_container_width=True)

with tab5:
    st.subheader("👥 Directorio del Personal")
    st.dataframe(df_personal, use_container_width=True)
