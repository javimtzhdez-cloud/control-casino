import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, time, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

ARCHIVO_EVENTOS = "eventos_casinos.csv"
ARCHIVO_PERSONAL = "personal_casinos.csv"
ARCHIVO_PAGOS = "pagos_casinos.csv"

st.set_page_config(page_title="Control de Casinos, Pagos y Sobres", page_icon="🎰", layout="wide")

st.title("🎰 Control Inteligente, Calendario, Pagos y Sobres - Casinos")
st.markdown("Gestión de eventos por casino, validación de horarios (máximo 3:00 AM fin / 10:00 PM inicio) y turnos de meseros.")

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
    if "Hora" not in df_eventos.columns:
        df_eventos["Hora"] = "19:00"
    if "Anticipo" not in df_eventos.columns:
        df_eventos["Anticipo"] = 1000.0
    if "Pago_Monto" not in df_eventos.columns:
        df_eventos["Pago_Monto"] = 500.0
    df_eventos.to_csv(ARCHIVO_EVENTOS, index=False)
else:
    df_eventos = pd.DataFrame(columns=["Fecha", "Hora", "Casino_Evento", "Nombre_Evento", "Tipo_Evento", "Anticipo", "Pago_Monto"])

# Cargar pagos generales
if os.path.exists(ARCHIVO_PAGOS):
    df_pagos = pd.read_csv(ARCHIVO_PAGOS)
else:
    df_pagos = pd.DataFrame(columns=["Fecha", "Casino", "Concepto", "Monto", "Estatus", "Metodo"])

def parse_time(t_str):
    try:
        return datetime.strptime(str(t_str).strip(), "%H:%M").time()
    except:
        return time(19, 0)

def time_to_minutes(t):
    return t.hour * 60 + t.minute

def verificar_conflicto_horario(df_ev, fecha_str, hora_inicio_t):
    nuevo_start_min = time_to_minutes(hora_inicio_t)
    
    # Validar límite de 10:00 PM (22:00 hrs)
    if nuevo_start_min > 22 * 60:
        return False, "❌ El horario límite de inicio es a las 10:00 PM (22:00 hrs) para que el evento termine a más tardar a las 3:00 AM."

    new_citation_min = nuevo_start_min - 90        # 1.5h antes cita meseros
    new_end_with_gap_min = nuevo_start_min + 300 + 180  # 5h evento + 3h diferencia

    if not df_ev.empty:
        misma_fecha = df_ev[df_ev["Fecha"] == fecha_str]
        for _, row in misma_fecha.iterrows():
            ex_start_t = parse_time(row.get("Hora", "19:00"))
            ex_start_min = time_to_minutes(ex_start_t)
            
            ex_citation_min = ex_start_min - 90
            ex_end_with_gap_min = ex_start_min + 300 + 180
            
            if max(new_citation_min, ex_citation_min) < min(new_end_with_gap_min, ex_end_with_gap_min):
                cita_ex_str = (datetime.combine(datetime.today(), ex_start_t) - timedelta(minutes=90)).strftime("%H:%M")
                fin_ex_str = (datetime.combine(datetime.today(), ex_start_t) + timedelta(minutes=300)).strftime("%H:%M")
                return False, f"❌ Conflicto de personal: Ya hay evento en **{row['Casino_Evento']}** ({row['Nombre_Evento']}) de {row['Hora']} a {fin_ex_str} (cita meseros {cita_ex_str}). Se requieren 3 horas de diferencia entre turnos."

    return True, "Disponible"

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
        start_t = parse_time(row_data.get('Hora', '19:00'))
        cita_t = datetime.combine(datetime.today(), start_t) - timedelta(minutes=90)
        fin_t = datetime.combine(datetime.today(), start_t) + timedelta(minutes=300)
        
        content = [
            Paragraph(f"<b>Casino:</b> {row_data['Casino_Evento']} | <b>Fecha:</b> {row_data['Fecha']}", style_title),
            Spacer(1, 2),
            Paragraph(f"<b>Evento:</b> {row_data['Nombre_Evento']} ({row_data['Tipo_Evento']})", style_body),
            Spacer(1, 2),
            Paragraph(f"⏰ <b>Cita Meseros:</b> {cita_t.strftime('%H:%M')} hrs | <b>Inicio:</b> {row_data.get('Hora', '19:00')} | <b>Fin:</b> {fin_t.strftime('%H:%M')}", style_body),
            Spacer(1, 2),
            Paragraph(f"💵 <b>Anticipo:</b> ${row_data.get('Anticipo', 0):,.2f} MXN", style_money)
        ]
        
        label_table = Table([[content]], colWidths=[270], rowHeights=[105])
        label_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#9ca3af')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
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
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(main_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 Registrar Evento", "📅 Calendario y Casinos", "✉️ Resumen de Eventos", "💰 Control de Pagos", "👥 Directorio Personal"])

with tab1:
    st.subheader("Registrar Evento y Validación de Horarios")
    st.markdown("1. Primero selecciona el **Casino**, la **Fecha** y la **Hora**.\n2. El sistema calcula automáticamente la cita de los meseros (1.5h antes), duración (5h) y verifica la regla de 3 horas de diferencia entre eventos (límite de inicio a las 10:00 PM para terminar a las 3:00 AM).")
    
    with st.form("form_evento_reglas", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            casino_evento = st.selectbox("1. Selecciona el Casino", ["Casino 1", "Casino 2", "Casino 3"])
            fecha = st.date_input("2. Fecha del Evento", value=datetime.now())
            hora_inicio = st.time_input("3. Hora de Inicio del Evento", value=time(19, 0))
        with col2:
            tipo_evento = st.selectbox("Tipo de Evento", [
                "Boda", "XV Años", "Cumpleaños / Festejo", "Evento Corporativo", "Comida / Cena Privada", "Otro"
            ])
            nombre_evento = st.text_input("Nombre del Evento (ej. Boda de los 15s)")
            anticipo = st.number_input("Dinero de Apartado / Anticipo ($ MXN)", min_value=0.0, value=1000.0, step=100.0)
        
        submit_btn = st.form_submit_button("Verificar Disponibilidad y Guardar Evento")
        
        if submit_btn:
            if not nombre_evento.strip():
                st.error("Por favor ingresa el nombre del evento.")
            else:
                fecha_str = fecha.strftime("%Y-%m-%d")
                hora_str = hora_inicio.strftime("%H:%M")
                
                valido, mensaje_error = verificar_conflicto_horario(df_eventos, fecha_str, hora_inicio)
                
                if not valido:
                    st.error(mensaje_error)
                else:
                    nuevo_registro = pd.DataFrame({
                        "Fecha": [fecha_str],
                        "Hora": [hora_str],
                        "Casino_Evento": [casino_evento],
                        "Nombre_Evento": [nombre_evento.strip()],
                        "Tipo_Evento": [tipo_evento],
                        "Anticipo": [anticipo],
                        "Pago_Monto": [500.0]
                    })
                    df_eventos = pd.concat([df_eventos, nuevo_registro], ignore_index=True)
                    df_eventos.to_csv(ARCHIVO_EVENTOS, index=False)
                    
                    cita_meseros = (datetime.combine(datetime.today(), hora_inicio) - timedelta(minutes=90)).strftime("%H:%M")
                    fin_evento = (datetime.combine(datetime.today(), hora_inicio) + timedelta(minutes=300)).strftime("%H:%M")
                    
                    st.success(f"✅ **¡Evento Registrado con Éxito!**\n\n"
                               f"• **Casino:** {casino_evento}\n"
                               f"• **Fecha y Hora:** {fecha_str} a las {hora_str} hrs\n"
                               f"• **Cita de Meseros:** {cita_meseros} hrs (1.5h antes)\n"
                               f"• **Fin del Evento:** {fin_evento} hrs (5 horas de duración)\n"
                               f"• **Anticipo:** ${anticipo:,.2f} MXN")
                    st.rerun()

with tab2:
    st.subheader("📅 Calendario y Vista por Casino")
    if df_eventos.empty:
        st.info("Aún no hay eventos registrados.")
    else:
        casino_seleccionado = st.selectbox("Selecciona un Casino para ver disponibilidad y eventos:", ["Todos los Casinos", "Casino 1", "Casino 2", "Casino 3"])
        df_vista = df_eventos.copy()
        if casino_seleccionado != "Todos los Casinos":
            df_vista = df_vista[df_vista["Casino_Evento"] == casino_seleccionado]
            
        st.markdown(f"### Mostrando eventos para: **{casino_seleccionado}**")
        st.dataframe(df_vista.sort_values(by=["Fecha", "Hora"]), use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗓️ Agenda de Eventos y Horarios de Meseros")
        for index, row in df_eventos.sort_values(by=["Fecha", "Hora"]).iterrows():
            start_t = parse_time(row.get('Hora', '19:00'))
            cita_t = datetime.combine(datetime.today(), start_t) - timedelta(minutes=90)
            fin_t = datetime.combine(datetime.today(), start_t) + timedelta(minutes=300)
            st.info(f"📅 **{row['Fecha']}** | 🎰 **{row['Casino_Evento']}** | ⏰ Inicio: **{row.get('Hora', '19:00')}** (Cita meseros: **{cita_t.strftime('%H:%M')}** | Fin: **{fin_t.strftime('%H:%M')}**) | 🎉 **{row['Nombre_Evento']}** ({row['Tipo_Evento']}) — Apartado: **${row.get('Anticipo', 0):,.2f}**")

        if st.checkbox("Habilitar opción para eliminar un evento"):
            idx_del = st.number_input("Número de fila a eliminar del evento", min_value=0, max_value=max(0, len(df_eventos)-1), step=1)
            if st.button("Eliminar Evento Seleccionado"):
                df_eventos = df_eventos.drop(idx_del).reset_index(drop=True)
                df_eventos.to_csv(ARCHIVO_EVENTOS, index=False)
                st.warning("Evento eliminado.")
                st.rerun()

with tab3:
    st.subheader("✉️ Resumen de Eventos y Horarios para Imprimir")
    if df_eventos.empty:
        st.info("No hay eventos registrados todavía.")
    else:
        fechas_disponibles = sorted(df_eventos["Fecha"].unique(), reverse=True)
        fecha_pago_sel = st.selectbox("Selecciona la Fecha:", fechas_disponibles)
        
        df_actuales = df_eventos[df_eventos["Fecha"] == fecha_pago_sel]
        
        filtro_sobre_casino = st.selectbox("Filtrar por Casino:", ["Todos los Casinos", "Casino 1", "Casino 2", "Casino 3"], key="filtro_sobre")
        if filtro_sobre_casino != "Todos los Casinos":
            df_actuales = df_actuales[df_actuales["Casino_Evento"] == filtro_sobre_casino]
            
        if not df_actuales.empty:
            pdf_bytes = generar_pdf_etiquetas(df_actuales, fecha_pago_sel)
            st.download_button(
                label="🖨️ Descargar PDF de Resumen de Eventos",
                data=pdf_bytes,
                file_name=f"resumen_eventos_{fecha_pago_sel}.pdf",
                mime="application/pdf",
                type="primary"
            )
        
        st.markdown("---")
        for _, row in df_actuales.iterrows():
            start_t = parse_time(row.get('Hora', '19:00'))
            cita_t = datetime.combine(datetime.today(), start_t) - timedelta(minutes=90)
            fin_t = datetime.combine(datetime.today(), start_t) + timedelta(minutes=300)
            
            with st.container(border=True):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown(f"### 🎰 **{row['Casino_Evento']}**")
                    st.markdown(f"📅 **Fecha:** {row['Fecha']}")
                    st.markdown(f"⏰ **Cita Meseros:** {cita_t.strftime('%H:%M')} hrs")
                    st.markdown(f"🚀 **Inicio Evento:** {row.get('Hora', '19:00')} hrs | 🏁 **Fin:** {fin_t.strftime('%H:%M')} hrs")
                with col_s2:
                    st.markdown(f"🎉 **Evento:** {row['Nombre_Evento']} ({row['Tipo_Evento']})")
                    st.markdown(f"💵 **Anticipo / Apartado:** `$%0.2f MXN`" % row.get('Anticipo', 0))

with tab4:
    st.subheader("💰 Control de Pagos y Anticipos Generales")
    if df_eventos.empty:
        st.info("Aún no hay eventos registrados.")
    else:
        total_anticipos = df_eventos["Anticipo"].sum()
        st.metric(label="Total Acumulado de Anticipos", value=f"${total_anticipos:,.2f} MXN")
        st.dataframe(df_eventos[["Fecha", "Hora", "Casino_Evento", "Nombre_Evento", "Tipo_Evento", "Anticipo"]], use_container_width=True)

with tab5:
    st.subheader("👥 Directorio del Personal")
    st.markdown("Lista de trabajadores registrados y opción para agregar nuevos miembros.")
    
    st.dataframe(df_personal, use_container_width=True)
    
    with st.form("form_nuevo_empleado", clear_on_submit=True):
        st.markdown("### Agregar Nuevo Trabajador")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            nuevo_nombre = st.text_input("Nombre Completo")
        with col_b:
            nuevo_puesto = st.selectbox("Cargo / Puesto", ["Mesero", "Garrotero", "Barra", "Capitán", "Hostess", "Seguridad", "Otro"])
        with col_c:
            nuevo_casino = st.selectbox("Casino Habitual", ["Casino 1", "Casino 2", "Casino 3"])
        
        btn_add = st.form_submit_button("Guardar Trabajador en el Directorio")
        if btn_add:
            if not nuevo_nombre.strip():
                st.error("Por favor ingresa el nombre del trabajador.")
            else:
                nueva_fila = pd.DataFrame({
                    "Nombre": [nuevo_nombre.strip()],
                    "Puesto": [nuevo_puesto],
                    "Casino_Habitual": [nuevo_casino]
                })
                df_personal = pd.concat([df_personal, nueva_fila], ignore_index=True)
                df_personal.to_csv(ARCHIVO_PERSONAL, index=False)
                st.success(f"✅ ¡Trabajador **{nuevo_nombre.strip()}** ({nuevo_puesto} - {nuevo_casino}) guardado con éxito!")
                st.rerun()
