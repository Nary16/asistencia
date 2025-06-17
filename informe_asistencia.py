import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import io

# === CONFIGURACIÓN DE LA CLASE PDF ===
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(162, 210, 255)
        self.cell(0, 10, 'Informe de Actividades realizadas INIFAR', border=0, ln=True, align='C', fill=True)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def check_page_break(self, height):
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()
            return True
        return False

def cargar_datos():
    """Carga datos desde Google Sheets y retorna dos DataFrames."""
    sheet_id = "1kQO659dZhq5lqwnXEmBmZ7zESlvk3BH7W9cClQ2CROk"
    url_actividades = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    url_resumen = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=1209679080"
    df_actividades = pd.read_csv(url_actividades)
    df_resumen = pd.read_csv(url_resumen)
    return df_actividades, df_resumen

def cargar_datos_cacheados():
    return cargar_datos()

def dibujar_tabla_resumen(pdf, resumen_fila):
    headers = [
        "Nombre", "Horas asignadas", "Horas totales", "Horas realizadas",
        "Porcentaje", "Horas pendientes", "Fecha de corte"
    ]
    col_widths = [40, 25, 25, 25, 25, 25, 25]

    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 10, "Corte de Horas", ln=True, align='C', fill=True)
    pdf.ln(2)

    pdf.set_font("Arial", 'B', 10)
    y_start = pdf.get_y()
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    total_width = sum(col_widths)
    x_start = pdf.l_margin + (page_width - total_width) / 2

    for i, header in enumerate(headers):
        x = x_start + sum(col_widths[:i])
        pdf.set_xy(x, y_start)
        pdf.multi_cell(col_widths[i], 5, header, border=1, align='C')

    pdf.set_font("Arial", '', 10)
    y_data = y_start + 10
    values = [str(resumen_fila[col].values[0]) for col in headers]
    for i, val in enumerate(values):
        x = x_start + sum(col_widths[:i])
        pdf.set_xy(x, y_data)
        pdf.cell(col_widths[i], 10, val, border=1, align='C')
    pdf.ln(20)

def dibujar_tabla_actividades(pdf, filas):
    cols = ["Tipo de horas", "Fecha de la Actividad", "Siglas de la Actividad", "Descripción de la Actividad", "Horas"]
    headers = ["Tipo de horas", "Fecha de Actividad", "Siglas", "Descripción de la actividad", "Horas"]

    def text_width(text):
        return pdf.get_string_width(str(text)) + 4

    max_widths = []
    for col, header in zip(cols, headers):
        max_w = text_width(header)
        max_w = max(max_w, max((text_width(str(val)) for val in filas[col]), default=0))
        max_widths.append(max_w)

    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    total_width = sum(max_widths)
    if total_width > page_width:
        idx_desc = cols.index("Descripción de la Actividad")
        exceso = total_width - page_width
        max_widths[idx_desc] = max(30, max_widths[idx_desc] - exceso)

    pdf.set_font("Arial", 'B', 11)
    y_start = pdf.get_y()
    x_pos = pdf.l_margin
    cell_height = 10
    for i, header in enumerate(headers):
        pdf.set_xy(x_pos, y_start)
        pdf.multi_cell(max_widths[i], cell_height / 2, header, border=1, align='C')
        x_pos += max_widths[i]
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    line_height = 5
    for _, fila in filas.iterrows():
        desc_text = str(fila["Descripción de la Actividad"])
        words = desc_text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if pdf.get_string_width(test_line) < max_widths[3]:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        cell_height_desc = line_height * len(lines)
        max_cell_height = max(cell_height, cell_height_desc)

        if pdf.check_page_break(max_cell_height):
            y_start = pdf.get_y()
            x_pos = pdf.l_margin
            for i, header in enumerate(headers):
                pdf.set_xy(x_pos, y_start)
                pdf.multi_cell(max_widths[i], cell_height / 2, header, border=1, align='C')
                x_pos += max_widths[i]
            pdf.ln()

        pdf.cell(max_widths[0], max_cell_height, str(fila["Tipo de horas"]), border=1)
        pdf.cell(max_widths[1], max_cell_height, str(fila["Fecha de la Actividad"]), border=1)
        pdf.cell(max_widths[2], max_cell_height, str(fila["Siglas de la Actividad"]), border=1)
        x_before = pdf.get_x()
        y_before = pdf.get_y()
        pdf.multi_cell(max_widths[3], line_height, desc_text, border=1)
        pdf.set_xy(x_before + max_widths[3], y_before)
        pdf.cell(max_widths[4], max_cell_height, str(fila["Horas"]), border=1)
        pdf.ln(max_cell_height)

def generar_pdf(asistente, df_resumen, df_actividades):
    resumen_fila = df_resumen[df_resumen["Nombre"] == asistente]
    filas = df_actividades[df_actividades["Nombre"] == asistente]

    if filas.empty:
        st.warning("No hay registros para este asistente.")
        return None

    pdf = PDF()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    if not resumen_fila.empty:
        dibujar_tabla_resumen(pdf, resumen_fila)

    dibujar_tabla_actividades(pdf, filas)
    return pdf

def cargar_contrasenas(sheet_id):
    url_contrasenas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=1209679080"  # usa el gid real de la hoja
    df_contrasenas = pd.read_csv(url_contrasenas)
    contrasenas = dict(zip(df_contrasenas["Nombre"], df_contrasenas["Contraseña"]))
    return contrasenas

sheet_id = "1kQO659dZhq5lqwnXEmBmZ7zESlvk3BH7W9cClQ2CROk"
contrasenas_validas = cargar_contrasenas(sheet_id)

# --- INTERFAZ STREAMLIT ---
from PIL import Image

# Cargar imagen desde archivo local
image = Image.open("logo oscuro.png")
st.image(image, width=500)

st.title("Generador de Informe INIFAR 📄")

df_actividades, df_resumen = cargar_datos_cacheados()
nombres = sorted(df_resumen["Nombre"].dropna().unique().tolist())
asistente = st.selectbox("Selecciona un asistente:", nombres)

import re
import unicodedata

def limpiar_nombre(nombre):
    nombre = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9_-]', '_', nombre)

# Inicializar session_state
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = None

# Si el usuario cambió
if st.session_state.usuario_autenticado != asistente:
    st.session_state.autenticado = False

# Mostrar input de contraseña si no ha sido autenticado
if not st.session_state.autenticado:
    password = st.text_input(f"Ingresa la contraseña para {asistente}:", type="password")
    if st.button("Validar contraseña"):
        if contrasenas_validas.get(asistente) == password:
            st.success("Contraseña correcta. Ya puedes generar el informe de asistencia.")
            st.session_state.autenticado = True
            st.session_state.usuario_autenticado = asistente
        else:
            st.error("Contraseña incorrecta.")
            st.session_state.autenticado = False

# Si autenticado, mostrar botón para generar PDF
if st.session_state.autenticado and st.session_state.usuario_autenticado == asistente:
    if st.button("Generar informe de asistencia"):
        filas_asistente = df_actividades[df_actividades["Nombre"] == asistente]
        resumen_asistente = df_resumen[df_resumen["Nombre"] == asistente]
        st.write(f"Datos actividades para {asistente}:")
        st.write(filas_asistente)
        st.write(f"Datos resumen para {asistente}:")
        st.write(resumen_asistente)
        pdf = generar_pdf(asistente, df_resumen, df_actividades)
        if pdf is not None:
            pdf_str = pdf.output(dest='S')
            pdf_bytes = pdf_str.encode('latin1')
            buffer = io.BytesIO(pdf_bytes)
            buffer.seek(0)
            st.download_button(
                label="📥 Descargar PDF",
                data=buffer,
                file_name=f"informe_{limpiar_nombre(asistente)}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("No hay datos para generar el PDF.")
