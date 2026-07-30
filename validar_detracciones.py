"""
Script para validar archivos PDF de detracciones SUNAT.
Valida que el nombre del archivo PDF coincida con la información contenida en el PDF:
1. Nombre/Razón Social del Proveedor
2. Número de Comprobante

Las equivalencias especiales de nombres se cargan desde equivalencias.json
(junto a este script). Los eventos y errores se registran en validador.log.
"""

import json
import logging
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
import unicodedata
from tkinter import filedialog, messagebox, ttk

import pdfplumber

logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "validador.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def cargar_equivalencias(ruta_json: str) -> dict:
    """
    Carga el diccionario de equivalencias especiales desde un archivo JSON.
    Clave: nombre en el archivo (normalizado en mayúsculas).
    Valor: texto que debe aparecer en el PDF para considerarlo válido.
    Retorna un diccionario vacío si el archivo no existe o es inválido.
    """
    try:
        with open(ruta_json, encoding="utf-8") as f:
            datos = json.load(f)
        if not isinstance(datos, dict):
            raise ValueError("El archivo de equivalencias debe contener un objeto JSON")
        return {str(clave).upper(): str(valor).upper() for clave, valor in datos.items()}
    except FileNotFoundError:
        logger.info("No se encontró %s; no se aplicarán equivalencias especiales.", ruta_json)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        logger.error("No se pudo cargar el archivo de equivalencias %s: %s", ruta_json, e)
    return {}


# Diccionario de equivalencias especiales para nombres que no pueden ser validados automáticamente
EQUIVALENCIAS_ESPECIALES = cargar_equivalencias(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "equivalencias.json")
)


def extraer_info_pdf(pdf_path: str) -> dict:
    """
    Extrae la información relevante del PDF de detracción.
    Retorna un diccionario con el nombre del proveedor y número de comprobante.
    """
    resultado = {
        "nombre_proveedor": None,
        "numero_comprobante": None,
        "texto_completo": ""
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    texto_completo += texto + "\n"

            resultado["texto_completo"] = texto_completo

            # Buscar Nombre/Razón Social del Proveedor
            # El texto puede aparecer como "Nombre/Razón Socila del Proveedor" (con typo) o "Nombre/Razón Social del Proveedor"
            patron_proveedor = r"Nombre/Raz[oó]n\s+Soci(?:al|la)\s+del\s+Proveedor\s+(.+?)(?:\n|Tipo|$)"
            match_proveedor = re.search(patron_proveedor, texto_completo, re.IGNORECASE)
            if match_proveedor:
                resultado["nombre_proveedor"] = match_proveedor.group(1).strip()

            # Buscar Número de Comprobante - patrón flexible para capturar FE01, FC02, FF05, F253, F0Z1, F0D1, etc.
            patron_comprobante = r"N.mero\s+de\s+Comprobante\s+([A-Z][A-Z0-9]{1,3}\s*-\s*[0-9]+)"
            match_comprobante = re.search(patron_comprobante, texto_completo, re.IGNORECASE)
            if match_comprobante:
                resultado["numero_comprobante"] = match_comprobante.group(1).strip()

    except Exception as e:
        logger.exception("Error al leer el PDF %s", pdf_path)
        resultado["error"] = str(e)

    return resultado


def quitar_acentos(texto: str) -> str:
    """
    Elimina acentos y caracteres especiales como ñ -> n.
    """
    if not texto:
        return ""
    # Normalizar a forma NFD (descomponer caracteres acentuados)
    texto_normalizado = unicodedata.normalize('NFD', texto)
    # Eliminar marcas diacríticas (acentos)
    texto_sin_acentos = ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')
    return texto_sin_acentos


def normalizar_nombre_proveedor(nombre: str) -> str:
    """
    Normaliza el nombre del proveedor eliminando sufijos como S.R.L., S.A.C., etc.
    y espacios extras.
    """
    if not nombre:
        return ""

    # Quitar acentos y ñ
    nombre = quitar_acentos(nombre)

    # Convertir a mayúsculas y eliminar espacios extras
    nombre = nombre.upper().strip()

    # Eliminar signos especiales como +, -, &, etc.
    nombre = re.sub(r'[+\-&@#$%*]', ' ', nombre)

    # Lista de sufijos empresariales a eliminar
    sufijos = [
        r'\s+S\.?R\.?L\.?$',
        r'\s+S\.?A\.?C\.?$',
        r'\s+S\.?A\.?$',
        r'\s+S\.?A\.?A\.?$',
        r'\s+E\.?I\.?R\.?L\.?$',
        r'\s+LTDA\.?$',
        r'\s+SOCIEDAD\s+CIVIL.*$',
        r'\s+SOCIEDAD\s+ANONI.*$',
        r'\s+SOCIEDAD$',
    ]

    for sufijo in sufijos:
        nombre = re.sub(sufijo, '', nombre, flags=re.IGNORECASE)

    # Eliminar espacios múltiples
    nombre = re.sub(r'\s+', ' ', nombre)

    return nombre.strip()


def obtener_palabras_significativas(nombre: str, min_longitud: int = 3) -> set:
    """
    Extrae las palabras significativas de un nombre (ignorando palabras muy cortas).
    """
    if not nombre:
        return set()

    # Normalizar primero
    nombre = quitar_acentos(nombre).upper()

    # Eliminar signos especiales
    nombre = re.sub(r'[+\-&@#$%*().,]', ' ', nombre)

    # Palabras a ignorar (stop words empresariales)
    palabras_ignorar = {
        'S', 'A', 'C', 'SRL', 'SAC', 'SA', 'SAA', 'EIRL', 'LTDA',
        'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'Y', 'E', 'EN',
        'SOCIEDAD', 'CIVIL', 'ANONIMA', 'RESPONSABILIDAD', 'LIMITADA',
        'POR', 'PERU', 'PERUANA'
    }

    palabras = set()
    for palabra in nombre.split():
        palabra = palabra.strip()
        # Incluir palabras que tengan longitud mínima y no sean stop words
        if len(palabra) >= min_longitud and palabra not in palabras_ignorar:
            palabras.add(palabra)

    return palabras


def comparar_nombres_flexible(nombre_archivo: str, nombre_pdf: str) -> tuple:
    """
    Compara dos nombres de forma flexible.
    Retorna (es_valido, mensaje_detalle)
    """
    if not nombre_archivo or not nombre_pdf:
        return False, "Nombre vacío"

    # Comparación 0: Verificar equivalencias especiales primero
    nombre_archivo_upper = nombre_archivo.upper().strip()
    for clave, valor in EQUIVALENCIAS_ESPECIALES.items():
        if clave.upper() in nombre_archivo_upper or nombre_archivo_upper in clave.upper():
            # Verificar si el valor esperado está en el nombre del PDF
            if valor.upper() in nombre_pdf.upper():
                return True, f"Equivalencia especial: {clave[:30]}..."

    # Normalizar ambos nombres
    archivo_norm = normalizar_nombre_proveedor(nombre_archivo)
    pdf_norm = normalizar_nombre_proveedor(nombre_pdf)

    # Comparación 1: igualdad exacta después de normalizar
    if archivo_norm == pdf_norm:
        return True, "Coincidencia exacta"

    # Comparación 2: uno contiene al otro (sin espacios)
    archivo_sin_espacios = archivo_norm.replace(" ", "")
    pdf_sin_espacios = pdf_norm.replace(" ", "")

    if archivo_sin_espacios == pdf_sin_espacios:
        return True, "Coincide sin espacios"

    if archivo_sin_espacios in pdf_sin_espacios or pdf_sin_espacios in archivo_sin_espacios:
        return True, "Uno contiene al otro"

    # Comparación 3: la mayoría de las palabras significativas largas (4+ caracteres)
    # del nombre del archivo deben aparecer en el nombre del PDF. Una sola palabra en
    # común no basta: nombres distintos suelen compartir términos genéricos del sector.
    palabras_archivo = obtener_palabras_significativas(nombre_archivo)
    palabras_pdf = obtener_palabras_significativas(nombre_pdf)

    palabras_largas_archivo = {p for p in palabras_archivo if len(p) >= 4}
    palabras_largas_pdf = {p for p in palabras_pdf if len(p) >= 4}

    if palabras_largas_archivo and palabras_largas_pdf:
        palabras_comunes = palabras_largas_archivo & palabras_largas_pdf
        ratio = len(palabras_comunes) / len(palabras_largas_archivo)
        if palabras_comunes and ratio >= 0.6:
            return True, (
                f"Palabras en común ({len(palabras_comunes)}/{len(palabras_largas_archivo)}): "
                f"{', '.join(sorted(palabras_comunes))}"
            )

    return False, f"Sin coincidencia: Archivo='{archivo_norm}' vs PDF='{pdf_norm}'"


def normalizar_numero_comprobante(numero: str) -> str:
    """
    Normaliza el número de comprobante: elimina espacios, convierte a mayúsculas
    y quita los ceros a la izquierda del correlativo (E001-00009926 -> E001-9926).
    """
    if not numero:
        return ""

    # Eliminar todos los espacios
    numero = numero.replace(" ", "").upper()

    if "-" in numero:
        serie, _, correlativo = numero.partition("-")
        correlativo = correlativo.lstrip("0") or "0"
        numero = f"{serie}-{correlativo}"

    return numero


def validar_archivo(nombre_archivo: str, info_pdf: dict) -> dict:
    """
    Valida si el nombre del archivo coincide con la información del PDF.
    """
    resultado = {
        "archivo": nombre_archivo,
        "valido_proveedor": False,
        "valido_comprobante": False,
        "proveedor_extraido": False,
        "comprobante_extraido": False,
        "nombre_archivo_proveedor": "",
        "nombre_pdf_proveedor": "",
        "comprobante_archivo": "",
        "comprobante_pdf": "",
        "detalle_proveedor": "",
        "mensaje": ""
    }

    # Extraer partes del nombre del archivo (sin extensión)
    nombre_sin_extension = os.path.splitext(nombre_archivo)[0]

    # Patrón esperado: RUC_NOMBRE COMPROBANTE DETRACCION
    # Ejemplo: 1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION
    # Se toma el ÚLTIMO patrón con formato de comprobante: la razón social puede
    # contener cadenas con el mismo formato (ej. "A1-100").
    patron_comprobante_archivo = r'([A-Z][A-Z0-9]{1,3}-[0-9]+)'
    coincidencias = list(re.finditer(patron_comprobante_archivo, nombre_sin_extension, re.IGNORECASE))

    if not coincidencias:
        resultado["mensaje"] = "No se pudo encontrar el número de comprobante en el nombre del archivo"
        return resultado

    match_comprobante = coincidencias[-1]
    comprobante_archivo = match_comprobante.group(1)
    resultado["comprobante_archivo"] = comprobante_archivo

    # Obtener la parte del nombre antes del número de comprobante
    parte_inicial = nombre_sin_extension[:match_comprobante.start()].strip()

    # Separar RUC del nombre (después del primer guion bajo)
    if '_' in parte_inicial:
        _, nombre_proveedor_archivo = parte_inicial.split('_', 1)
        resultado["nombre_archivo_proveedor"] = nombre_proveedor_archivo.strip()
    else:
        resultado["nombre_archivo_proveedor"] = parte_inicial

    # Comparar nombre del proveedor usando la función flexible
    nombre_pdf = info_pdf.get("nombre_proveedor") or ""
    resultado["nombre_pdf_proveedor"] = nombre_pdf
    resultado["proveedor_extraido"] = bool(nombre_pdf)

    if nombre_pdf:
        es_valido_proveedor, detalle_proveedor = comparar_nombres_flexible(
            resultado["nombre_archivo_proveedor"],
            nombre_pdf
        )
        resultado["valido_proveedor"] = es_valido_proveedor
        resultado["detalle_proveedor"] = detalle_proveedor
    else:
        resultado["detalle_proveedor"] = "No se pudo extraer el proveedor del PDF"

    # Normalizar y comparar número de comprobante
    comprobante_pdf = info_pdf.get("numero_comprobante") or ""
    resultado["comprobante_pdf"] = comprobante_pdf
    resultado["comprobante_extraido"] = bool(comprobante_pdf)

    comprobante_archivo_normalizado = normalizar_numero_comprobante(resultado["comprobante_archivo"])
    comprobante_pdf_normalizado = normalizar_numero_comprobante(comprobante_pdf)

    if comprobante_archivo_normalizado and comprobante_pdf_normalizado:
        if comprobante_archivo_normalizado == comprobante_pdf_normalizado:
            resultado["valido_comprobante"] = True

    # Generar mensaje de resultado
    mensajes = []
    if not resultado["proveedor_extraido"]:
        mensajes.append("No se pudo extraer el proveedor del PDF")
    elif not resultado["valido_proveedor"]:
        mensajes.append(f"Proveedor no coincide: Archivo='{resultado['nombre_archivo_proveedor']}' vs PDF='{resultado['nombre_pdf_proveedor']}'")
    if not resultado["comprobante_extraido"]:
        mensajes.append("No se pudo extraer el comprobante del PDF")
    elif not resultado["valido_comprobante"]:
        mensajes.append(f"Comprobante no coincide: Archivo='{resultado['comprobante_archivo']}' vs PDF='{resultado['comprobante_pdf']}'")

    resultado["mensaje"] = " | ".join(mensajes) if mensajes else "OK"

    return resultado


class AplicacionValidador:
    def __init__(self, root):
        self.root = root
        self.root.title("Validador de Detracciones SUNAT")
        self.root.geometry("1000x600")
        self.root.minsize(900, 500)

        self.carpeta_seleccionada = tk.StringVar()
        self.resultados = []
        self.archivos_dict = {}  # Diccionario para mapear item_id -> ruta completa
        self.cola_resultados = None  # Cola para comunicar el hilo worker con la GUI
        self.correctos = 0
        self.incorrectos = 0

        self.crear_interfaz()
        self.crear_menu_contextual()

    def crear_interfaz(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame para selección de carpeta
        frame_carpeta = ttk.Frame(main_frame)
        frame_carpeta.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame_carpeta, text="Carpeta:").pack(side=tk.LEFT)

        entry_carpeta = ttk.Entry(frame_carpeta, textvariable=self.carpeta_seleccionada, width=80)
        entry_carpeta.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.btn_seleccionar = ttk.Button(frame_carpeta, text="Seleccionar Carpeta", command=self.seleccionar_carpeta)
        self.btn_seleccionar.pack(side=tk.LEFT, padx=5)

        self.btn_validar = ttk.Button(frame_carpeta, text="Validar Archivos", command=self.validar_archivos)
        self.btn_validar.pack(side=tk.LEFT, padx=5)

        # Frame para resultados con scrollbars
        frame_resultados = ttk.Frame(main_frame)
        frame_resultados.pack(fill=tk.BOTH, expand=True)

        # Crear Treeview para mostrar resultados
        columns = ("archivo", "proveedor", "comprobante", "estado", "detalle")
        self.tree = ttk.Treeview(frame_resultados, columns=columns, show="headings")

        # Configurar columnas - usar stretch=False para que el scroll horizontal funcione correctamente
        self.tree.heading("archivo", text="Archivo")
        self.tree.heading("proveedor", text="Proveedor OK")
        self.tree.heading("comprobante", text="Comprobante OK")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("detalle", text="Detalle")

        self.tree.column("archivo", width=400, minwidth=200, stretch=False)
        self.tree.column("proveedor", width=100, minwidth=80, anchor=tk.CENTER, stretch=False)
        self.tree.column("comprobante", width=120, minwidth=100, anchor=tk.CENTER, stretch=False)
        self.tree.column("estado", width=100, minwidth=80, anchor=tk.CENTER, stretch=False)
        self.tree.column("detalle", width=600, minwidth=300, stretch=False)

        # Scrollbars
        scrollbar_y = ttk.Scrollbar(frame_resultados, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_resultados, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Layout usando grid para que el scrollbar horizontal funcione correctamente
        frame_resultados.grid_rowconfigure(0, weight=1)
        frame_resultados.grid_columnconfigure(0, weight=1)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Vincular eventos de doble clic, Enter y clic derecho
        self.tree.bind("<Double-1>", self.abrir_archivo)
        self.tree.bind("<Return>", self.abrir_archivo)
        self.tree.bind("<Button-3>", self.mostrar_menu_contextual)

        # Frame para barra de progreso
        self.frame_progreso = ttk.Frame(main_frame)
        self.frame_progreso.pack(fill=tk.X, pady=(10, 0))

        self.label_progreso = ttk.Label(self.frame_progreso, text="")
        self.label_progreso.pack()
        self.label_progreso.pack_forget()  # Ocultar inicialmente

        self.barra_progreso = ttk.Progressbar(self.frame_progreso, mode='determinate', length=400)
        self.barra_progreso.pack(fill=tk.X, pady=(5, 0))
        self.barra_progreso.pack_forget()  # Ocultar inicialmente

        # Frame para resumen
        self.frame_resumen = ttk.Frame(main_frame)
        self.frame_resumen.pack(fill=tk.X, pady=(10, 0))

        self.label_resumen = ttk.Label(self.frame_resumen, text="")
        self.label_resumen.pack()

        # Configurar tags para colores
        self.tree.tag_configure('error', background='#ffcccc')
        self.tree.tag_configure('ok', background='#ccffcc')

    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta con PDFs de detracciones")
        if carpeta:
            self.carpeta_seleccionada.set(carpeta)

    def crear_menu_contextual(self):
        """Crea el menú contextual para clic derecho."""
        self.menu_contextual = tk.Menu(self.root, tearoff=0)
        self.menu_contextual.add_command(label="Abrir archivo", command=self.abrir_archivo_seleccionado)
        self.menu_contextual.add_command(label="Abrir ubicación", command=self.abrir_ubicacion)

    def mostrar_menu_contextual(self, event):
        """Muestra el menú contextual en la posición del clic."""
        # Seleccionar el item bajo el cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu_contextual.post(event.x_root, event.y_root)

    def obtener_ruta_archivo_seleccionado(self):
        """Obtiene la ruta completa del archivo seleccionado."""
        seleccion = self.tree.selection()
        if not seleccion:
            return None

        item_id = seleccion[0]
        return self.archivos_dict.get(item_id)

    def abrir_archivo(self, event=None):
        """Abre el archivo PDF con el programa predeterminado (doble clic o Enter)."""
        ruta = self.obtener_ruta_archivo_seleccionado()
        if ruta and os.path.exists(ruta):
            try:
                os.startfile(ruta)
            except OSError as e:
                logger.exception("No se pudo abrir el archivo %s", ruta)
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {str(e)}")
        elif ruta:
            messagebox.showwarning("Advertencia", "El archivo no existe.")

    def abrir_archivo_seleccionado(self):
        """Abre el archivo PDF seleccionado (desde menú contextual)."""
        self.abrir_archivo()

    def abrir_ubicacion(self):
        """Abre el explorador de Windows en la ubicación del archivo seleccionado."""
        ruta = self.obtener_ruta_archivo_seleccionado()
        if ruta and os.path.exists(ruta):
            try:
                # Normalizar la ruta a formato Windows (backslashes)
                ruta_windows = os.path.normpath(ruta)
                # Lista de argumentos SIN shell=True: evita inyección de comandos
                # a través de nombres de archivo maliciosos
                subprocess.run(["explorer", "/select,", ruta_windows])
            except OSError as e:
                logger.exception("No se pudo abrir la ubicación de %s", ruta)
                messagebox.showerror("Error", f"No se pudo abrir la ubicación: {str(e)}")
        elif ruta:
            messagebox.showwarning("Advertencia", "El archivo no existe.")

    def establecer_estado_procesando(self, procesando: bool):
        """Deshabilita los controles mientras se procesa para evitar dobles validaciones."""
        estado = "disabled" if procesando else "normal"
        self.btn_validar.config(state=estado)
        self.btn_seleccionar.config(state=estado)
        self.root.config(cursor="watch" if procesando else "")

    def validar_archivos(self):
        carpeta = self.carpeta_seleccionada.get()

        if not carpeta:
            messagebox.showwarning("Advertencia", "Por favor, seleccione una carpeta primero.")
            return

        if not os.path.isdir(carpeta):
            messagebox.showerror("Error", "La carpeta seleccionada no existe.")
            return

        # Obtener lista de archivos PDF
        archivos_pdf = [f for f in os.listdir(carpeta) if f.lower().endswith('.pdf')]

        if not archivos_pdf:
            messagebox.showinfo("Información", "No se encontraron archivos PDF en la carpeta seleccionada.")
            return

        # Limpiar resultados anteriores
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Limpiar diccionario de archivos y contadores
        self.archivos_dict.clear()
        self.label_resumen.config(text="")
        self.resultados = []
        self.correctos = 0
        self.incorrectos = 0

        # Mostrar y configurar barra de progreso
        self.label_progreso.pack()
        self.barra_progreso.pack(fill=tk.X, pady=(5, 0))
        self.barra_progreso['maximum'] = len(archivos_pdf)
        self.barra_progreso['value'] = 0

        self.establecer_estado_procesando(True)
        logger.info("Iniciando validación de %d archivos en %s", len(archivos_pdf), carpeta)

        # Procesar en un hilo separado para no congelar la interfaz
        self.cola_resultados = queue.Queue()
        hilo = threading.Thread(
            target=self.procesar_archivos_en_segundo_plano,
            args=(carpeta, archivos_pdf),
            daemon=True,
        )
        hilo.start()
        self.root.after(100, self.procesar_cola_resultados)

    def procesar_archivos_en_segundo_plano(self, carpeta, archivos_pdf):
        """Hilo worker: extrae y valida los PDFs sin tocar la interfaz."""
        total = len(archivos_pdf)
        try:
            for i, archivo in enumerate(archivos_pdf):
                ruta_completa = os.path.join(carpeta, archivo)

                # Extraer información del PDF
                info_pdf = extraer_info_pdf(ruta_completa)

                if "error" in info_pdf:
                    resultado = {
                        "archivo": archivo,
                        "valido_proveedor": False,
                        "valido_comprobante": False,
                        "proveedor_extraido": False,
                        "comprobante_extraido": False,
                        "mensaje": f"Error al leer PDF: {info_pdf['error']}"
                    }
                else:
                    # Validar archivo
                    resultado = validar_archivo(archivo, info_pdf)

                self.cola_resultados.put(("progreso", i, total, archivo, resultado, ruta_completa))

            self.cola_resultados.put(("fin",))
        except Exception as e:
            logger.exception("Error al procesar la carpeta %s", carpeta)
            self.cola_resultados.put(("error", str(e)))

    def procesar_cola_resultados(self):
        """Hilo principal: consume los resultados del worker y actualiza la interfaz."""
        try:
            while True:
                mensaje = self.cola_resultados.get_nowait()
                tipo = mensaje[0]
                if tipo == "progreso":
                    _, i, total, archivo, resultado, ruta_completa = mensaje
                    self.mostrar_resultado(i, total, archivo, resultado, ruta_completa)
                elif tipo == "fin":
                    self.finalizar_validacion()
                    return
                elif tipo == "error":
                    self.finalizar_validacion(con_error=mensaje[1])
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.procesar_cola_resultados)

    @staticmethod
    def simbolo_validacion(valido: bool, extraido: bool) -> str:
        """Símbolo para la columna: ✓ válido, ✗ inválido, — no se pudo extraer del PDF."""
        if valido:
            return "✓"
        return "✗" if extraido else "—"

    def mostrar_resultado(self, i, total, archivo, resultado, ruta_completa):
        """Actualiza la barra de progreso e inserta una fila en el treeview."""
        self.barra_progreso['value'] = i + 1
        self.label_progreso.config(text=f"Procesando: {archivo} ({i + 1}/{total})")

        self.resultados.append(resultado)

        es_valido = resultado["valido_proveedor"] and resultado["valido_comprobante"]

        proveedor_texto = self.simbolo_validacion(
            resultado["valido_proveedor"], resultado.get("proveedor_extraido", True)
        )
        comprobante_texto = self.simbolo_validacion(
            resultado["valido_comprobante"], resultado.get("comprobante_extraido", True)
        )
        estado_texto = "CORRECTO" if es_valido else "ERROR"

        tag = 'ok' if es_valido else 'error'

        if es_valido:
            self.correctos += 1
        else:
            self.incorrectos += 1

        # Insertar en el treeview y guardar la ruta en el diccionario
        item_id = self.tree.insert("", tk.END, values=(
            resultado["archivo"],
            proveedor_texto,
            comprobante_texto,
            estado_texto,
            resultado.get("mensaje", "")
        ), tags=(tag,))

        # Guardar la ruta completa del archivo
        self.archivos_dict[item_id] = ruta_completa

    def finalizar_validacion(self, con_error=None):
        """Restaura la interfaz y muestra el resumen (o el error) al terminar."""
        # Ocultar barra de progreso y limpiar texto
        self.barra_progreso.pack_forget()
        self.label_progreso.pack_forget()
        self.label_progreso.config(text="")
        self.establecer_estado_procesando(False)

        if con_error:
            logger.error("Validación interrumpida: %s", con_error)
            messagebox.showerror("Error", f"Error al procesar la carpeta: {con_error}")
            return

        # Actualizar resumen
        total = len(self.resultados)
        logger.info(
            "Validación completada: %d archivos | correctos: %d | con errores: %d",
            total, self.correctos, self.incorrectos
        )
        self.label_resumen.config(
            text=f"Total: {total} archivos | ✓ Correctos: {self.correctos} | ✗ Con errores: {self.incorrectos}"
        )

        if self.incorrectos > 0:
            messagebox.showinfo(
                "Validación Completada",
                f"Se encontraron {self.incorrectos} archivo(s) con errores de validación.\n"
                f"Los archivos con errores están resaltados en rojo."
            )
        else:
            messagebox.showinfo(
                "Validación Completada",
                f"¡Todos los {total} archivos pasaron la validación correctamente!"
            )


def main():
    root = tk.Tk()
    app = AplicacionValidador(root)
    root.mainloop()


if __name__ == "__main__":
    main()
