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
    sheet_id = "1vX-OT6TrkNzEW-2hyBrxJJKAbQQKtqyFaMWiKjDTbow"
    url_actividades = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=796485673"
    url_resumen = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=882546156"
    df_actividades = pd.read_csv(url_actividades)
    df_resumen = pd.read_csv(url_resumen)
    return df_actividades, df_resumen

def cargar_datos_cacheados():
    return cargar_datos()

def dibujar_tabla_resumen(pdf, resumen_fila):
    headers = [
        "Nombre del Asistente", "Horas asignadas", "Horas totales", "Horas realizadas",
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
    # Ajusta aquí los nombres de columnas según los datos reales de la hoja de actividades
    # Definir columnas esperadas y filtrar solo las presentes
    cols_all = [
        "Nombre del Asistente",
        "Tipo de horas",
        "Fecha de la Actividad",
        "Siglas de la Actividad",
        "Descripción de la Actividad",
        "Cantidad de horas"
    ]
    cols = [c for c in cols_all if c in filas.columns]
    headers = cols.copy()
    print("Columnas en actividades:", filas.columns.tolist())

    # Anchos mínimos y máximos sugeridos para cada columna (ajustar a cantidad de columnas)
    min_widths_dict = {
        "Nombre del Asistente": 28,
        "Tipo de horas": 22,
        "Fecha de la Actividad": 22,
        "Siglas de la Actividad": 22,
        "Descripción de la Actividad": 50,
        "Cantidad de horas": 18
    }
    max_widths_dict = {
        "Nombre del Asistente": 40,
        "Tipo de horas": 28,
        "Fecha de la Actividad": 28,
        "Siglas de la Actividad": 28,
        "Descripción de la Actividad": 80,
        "Cantidad de horas": 22
    }
    min_widths = [min_widths_dict[c] for c in cols]
    max_widths = [max_widths_dict[c] for c in cols]

    def text_width(text):
        return pdf.get_string_width(str(text)) + 4

    # Calcular ancho óptimo por columna
    col_widths = []
    for i, col in enumerate(cols):
        w = text_width(headers[i])
        w = max(w, max((text_width(str(val)) for val in filas[col]), default=0))
        w = max(w, min_widths[i])
        w = min(w, max_widths[i])
        col_widths.append(w)

    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    total_width = sum(col_widths)
    # Si la suma excede el ancho de página, reducir proporcionalmente (excepto la columna de descripción)
    if total_width > page_width:
        exceso = total_width - page_width
        # Repartir el exceso entre todas las columnas menos la de descripción
        idx_desc = None
        for i, col in enumerate(cols):
            if "Descripción" in col:
                idx_desc = i
                break
        # Calcular el total de ancho de las columnas a reducir
        ancho_reducible = sum(col_widths) - col_widths[idx_desc] if idx_desc is not None else sum(col_widths)
        for i in range(len(col_widths)):
            if i != idx_desc and ancho_reducible > 0:
                reduccion = exceso * (col_widths[i] / ancho_reducible)
                col_widths[i] = max(min_widths[i], col_widths[i] - reduccion)
        # Si aún sobra, reducir la columna de descripción pero nunca por debajo de su mínimo
        total_width = sum(col_widths)
        if total_width > page_width and idx_desc is not None:
            col_widths[idx_desc] = max(min_widths[idx_desc], col_widths[idx_desc] - (total_width - page_width))

    total_width = sum(col_widths)
    x_start = pdf.l_margin + max(0, (page_width - total_width) / 2)

    # Encabezados con color de fondo
    def dibujar_encabezados():
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(200, 220, 255)
        y_start = pdf.get_y()
        for i, header in enumerate(headers):
            x = x_start + sum(col_widths[:i])
            pdf.set_xy(x, y_start)
            pdf.multi_cell(col_widths[i], 6, header, border=1, align='C', fill=True)
        pdf.ln(6)

    dibujar_encabezados()

    # Filas de datos
    pdf.set_font("Arial", '', 8)
    for _, fila in filas.iterrows():
        y_data = pdf.get_y()
        valores = [str(fila[col]) if col in fila else "" for col in cols]
        # Limitar cada celda a máximo 5 líneas y eliminar líneas repetidas
        for i, valor in enumerate(valores):
            lines = valor.split('\n')
            seen = set()
            unique_lines = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped and line_stripped not in seen:
                    unique_lines.append(line_stripped)
                    seen.add(line_stripped)
            if len(unique_lines) > 5:
                unique_lines = unique_lines[:5]
                unique_lines[-1] += ' ...'
            valores[i] = '\n'.join(unique_lines)

        # Calcular la altura máxima estimando el número de líneas por celda
        alturas = []
        for i, valor in enumerate(valores):
            n_lines = valor.count('\n') + 1 if valor else 1
            alturas.append(n_lines * 8)  # 8 es la altura por línea
        max_cell_height = max(alturas) if alturas else 8

        # Si se va a saltar de página, redibujar encabezados
        if pdf.get_y() + max_cell_height > pdf.page_break_trigger:
            pdf.add_page()
            dibujar_encabezados()
            y_data = pdf.get_y()

        # Dibujar cada celda solo una vez, centrando verticalmente el texto si es necesario
        interlineado = 5  # Menor interlineado para filas más compactas
        max_y = y_data
        for i, valor in enumerate(valores):
            x = x_start + sum(col_widths[:i])
            cell_height = (valor.count('\n') + 1) * interlineado
            v_offset = (max_cell_height - cell_height) / 2 if max_cell_height > cell_height else 0
            # Si es la columna de siglas, usar fuente 7
            if headers[i] == "Siglas de la Actividad":
                pdf.set_font("Arial", '', 7)
            else:
                pdf.set_font("Arial", '', 8)
            pdf.set_xy(x, y_data + v_offset)
            pdf.multi_cell(col_widths[i], interlineado, valor, border=1, align='C')
            # Actualizar la posición máxima alcanzada por cualquier celda
            max_y = max(max_y, pdf.get_y())
        # Avanza la posición vertical justo después de la última línea impresa de la fila
        pdf.set_y(max_y + 2)

def generar_pdf(asistente, df_resumen, df_actividades):
    resumen_fila = df_resumen[df_resumen["Nombre del Asistente"] == asistente]
    filas = df_actividades[df_actividades["Nombre del Asistente"] == asistente]

    if filas.empty:
        st.warning("No hay registros para este asistente.")
        return None

    pdf = PDF()
    pdf.set_left_margin(5)
    pdf.set_right_margin(5)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)

    if not resumen_fila.empty:
        dibujar_tabla_resumen(pdf, resumen_fila)

    dibujar_tabla_actividades(pdf, filas)
    return pdf

def cargar_contrasenas(sheet_id):
    url_contrasenas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=882546156"  # usa el gid real de la hoja
    df_contrasenas = pd.read_csv(url_contrasenas)
    print("Columnas encontradas en contraseñas:", df_contrasenas.columns.tolist())
    col_contra = None
    col_nombre = None
    for col in df_contrasenas.columns:
        if col.strip().lower() == "contraseña":
            col_contra = col
        if col.strip().lower() == "nombre":
            col_nombre = col
    if not col_contra:
        col_contra = df_contrasenas.columns[-1]
    if not col_nombre:
        col_nombre = df_contrasenas.columns[0]
    contrasenas = dict(zip(df_contrasenas[col_nombre], df_contrasenas[col_contra]))
    return contrasenas

sheet_id = "1vX-OT6TrkNzEW-2hyBrxJJKAbQQKtqyFaMWiKjDTbow"
contrasenas_validas = cargar_contrasenas(sheet_id)

# --- INTERFAZ STREAMLIT ---
from PIL import Image

# Cargar imagen desde archivo local
image = Image.open("logo claro.png")
st.image(image, width=500)

st.title("Generador de Informe INIFAR 📄")

df_actividades, df_resumen = cargar_datos_cacheados()
nombres = sorted(df_resumen["Nombre del Asistente"].dropna().unique().tolist())
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
        contra_real = contrasenas_validas.get(asistente, "")
        if contra_real.strip() == password.strip():
            st.success("Contraseña correcta. Ya puedes generar el informe de asistencia.")
            st.session_state.autenticado = True
            st.session_state.usuario_autenticado = asistente
        else:
            st.error("Contraseña incorrecta.")
            st.session_state.autenticado = False

# Si autenticado, mostrar botón para generar PDF
if st.session_state.autenticado and st.session_state.usuario_autenticado == asistente:
    if st.button("Generar informe de asistencia"):
        filas_asistente = df_actividades[df_actividades["Nombre del Asistente"] == asistente]
        resumen_asistente = df_resumen[df_resumen["Nombre del Asistente"] == asistente]
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
