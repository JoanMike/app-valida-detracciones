"""
Script para validar archivos PDF de detracciones SUNAT.
Valida que el nombre del archivo PDF coincida con la información contenida en el PDF:
1. Nombre/Razón Social del Proveedor
2. Número de Comprobante
"""

import os
import re
import unicodedata
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pdfplumber
from datetime import datetime


# Diccionario de equivalencias especiales para nombres que no pueden ser validados automáticamente
# Clave: nombre en el archivo (normalizado en mayúsculas)
# Valor: texto que debe aparecer en el PDF para considerarlo válido
EQUIVALENCIAS_ESPECIALES = {
    "CONSULT. INTEG. DE MKT Y COMUNIC. NOVACOM": "CONSULTORA INTEGRAL DE MARKETING Y",
}


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
            patron_proveedor = r"Nombre/Raz[oó]n\s+Soci[al][al]\s+del\s+Proveedor\s+(.+?)(?:\n|Tipo|$)"
            match_proveedor = re.search(patron_proveedor, texto_completo, re.IGNORECASE)
            if match_proveedor:
                resultado["nombre_proveedor"] = match_proveedor.group(1).strip()
            
            # Buscar Número de Comprobante - patrón flexible para capturar FE01, FC02, FF05, F253, F0Z1, F0D1, etc.
            patron_comprobante = r"N.mero\s+de\s+Comprobante\s+([A-Z][A-Z0-9]{1,3}\s*-\s*[0-9]+)"
            match_comprobante = re.search(patron_comprobante, texto_completo, re.IGNORECASE)
            if match_comprobante:
                resultado["numero_comprobante"] = match_comprobante.group(1).strip()
                
    except Exception as e:
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
    
    # Comparación 3: por palabras significativas en común
    palabras_archivo = obtener_palabras_significativas(nombre_archivo)
    palabras_pdf = obtener_palabras_significativas(nombre_pdf)
    
    if palabras_archivo and palabras_pdf:
        palabras_comunes = palabras_archivo & palabras_pdf
        
        # Si hay al menos una palabra significativa en común
        if len(palabras_comunes) >= 1:
            # Si la palabra común es significativa (ej: nombre principal de empresa)
            # Considerar válido si al menos una palabra de 4+ caracteres coincide
            palabras_largas_comunes = {p for p in palabras_comunes if len(p) >= 4}
            if palabras_largas_comunes:
                return True, f"Palabras en común: {', '.join(sorted(palabras_largas_comunes))}"
    
    return False, f"Sin coincidencia: Archivo='{archivo_norm}' vs PDF='{pdf_norm}'"


def normalizar_numero_comprobante(numero: str) -> str:
    """
    Normaliza el número de comprobante eliminando espacios alrededor del guion.
    """
    if not numero:
        return ""
    
    # Eliminar todos los espacios
    numero = numero.replace(" ", "").upper()
    
    return numero


def validar_archivo(nombre_archivo: str, info_pdf: dict) -> dict:
    """
    Valida si el nombre del archivo coincide con la información del PDF.
    """
    resultado = {
        "archivo": nombre_archivo,
        "valido_proveedor": False,
        "valido_comprobante": False,
        "nombre_archivo_proveedor": "",
        "nombre_pdf_proveedor": "",
        "comprobante_archivo": "",
        "comprobante_pdf": "",
        "mensaje": ""
    }
    
    # Extraer partes del nombre del archivo (sin extensión)
    nombre_sin_extension = os.path.splitext(nombre_archivo)[0]
    
    # Patrón esperado: RUC_NOMBRE COMPROBANTE DETRACCION
    # Ejemplo: 1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION
    
    # Buscar el patrón del número de comprobante en el nombre del archivo
    # Patrón flexible: letra inicial + 1-3 alfanuméricos, guion, y más dígitos
    # Ejemplos: E001, FE01, FC02, FF05, F253, FS02, F0Z1, F0D1
    patron_comprobante_archivo = r'([A-Z][A-Z0-9]{1,3}-[0-9]+)'
    match_comprobante = re.search(patron_comprobante_archivo, nombre_sin_extension, re.IGNORECASE)
    
    if match_comprobante:
        comprobante_archivo = match_comprobante.group(1)
        resultado["comprobante_archivo"] = comprobante_archivo
        
        # Obtener la parte del nombre antes del número de comprobante
        pos_comprobante = match_comprobante.start()
        parte_inicial = nombre_sin_extension[:pos_comprobante].strip()
        
        # Separar RUC del nombre (después del primer guion bajo)
        if '_' in parte_inicial:
            _, nombre_proveedor_archivo = parte_inicial.split('_', 1)
            resultado["nombre_archivo_proveedor"] = nombre_proveedor_archivo.strip()
        else:
            resultado["nombre_archivo_proveedor"] = parte_inicial
    else:
        resultado["mensaje"] = "No se pudo encontrar el número de comprobante en el nombre del archivo"
        return resultado
    
    # Comparar nombre del proveedor usando la función flexible
    resultado["nombre_pdf_proveedor"] = info_pdf.get("nombre_proveedor", "")
    
    es_valido_proveedor, detalle_proveedor = comparar_nombres_flexible(
        resultado["nombre_archivo_proveedor"],
        resultado["nombre_pdf_proveedor"]
    )
    resultado["valido_proveedor"] = es_valido_proveedor
    resultado["detalle_proveedor"] = detalle_proveedor
    
    # Normalizar y comparar número de comprobante
    comprobante_archivo_normalizado = normalizar_numero_comprobante(resultado["comprobante_archivo"])
    comprobante_pdf = info_pdf.get("numero_comprobante", "")
    comprobante_pdf_normalizado = normalizar_numero_comprobante(comprobante_pdf)
    
    resultado["comprobante_pdf"] = comprobante_pdf
    
    if comprobante_archivo_normalizado and comprobante_pdf_normalizado:
        if comprobante_archivo_normalizado == comprobante_pdf_normalizado:
            resultado["valido_comprobante"] = True
    
    # Generar mensaje de resultado
    mensajes = []
    if not resultado["valido_proveedor"]:
        mensajes.append(f"Proveedor no coincide: Archivo='{resultado['nombre_archivo_proveedor']}' vs PDF='{resultado['nombre_pdf_proveedor']}'")
    if not resultado["valido_comprobante"]:
        mensajes.append(f"Comprobante no coincide: Archivo='{resultado['comprobante_archivo']}' vs PDF='{resultado['comprobante_pdf']}'")
    
    resultado["mensaje"] = " | ".join(mensajes) if mensajes else "OK"
    
    return resultado


def procesar_carpeta(carpeta: str) -> list:
    """
    Procesa todos los archivos PDF en la carpeta y retorna los resultados de validación.
    """
    resultados = []
    
    # Listar todos los archivos PDF en la carpeta
    archivos_pdf = [f for f in os.listdir(carpeta) if f.lower().endswith('.pdf')]
    
    for archivo in archivos_pdf:
        ruta_completa = os.path.join(carpeta, archivo)
        
        # Extraer información del PDF
        info_pdf = extraer_info_pdf(ruta_completa)
        
        if "error" in info_pdf:
            resultados.append({
                "archivo": archivo,
                "valido_proveedor": False,
                "valido_comprobante": False,
                "mensaje": f"Error al leer PDF: {info_pdf['error']}"
            })
            continue
        
        # Validar archivo
        resultado = validar_archivo(archivo, info_pdf)
        resultados.append(resultado)
    
    return resultados


class AplicacionValidador:
    def __init__(self, root):
        self.root = root
        self.root.title("Validador de Detracciones SUNAT - Jose Miguel Maldonado Garcia")
        self.root.geometry("1000x600")
        self.root.minsize(900, 500)
        
        self.carpeta_seleccionada = tk.StringVar()
        self.resultados = []
        self.archivos_dict = {}  # Diccionario para mapear item_id -> ruta completa
        
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
        
        btn_seleccionar = ttk.Button(frame_carpeta, text="Seleccionar Carpeta", command=self.seleccionar_carpeta)
        btn_seleccionar.pack(side=tk.LEFT, padx=5)
        
        btn_validar = ttk.Button(frame_carpeta, text="Validar Archivos", command=self.validar_archivos)
        btn_validar.pack(side=tk.LEFT, padx=5)
        
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
        
        # Vincular eventos de doble clic y clic derecho
        self.tree.bind("<Double-1>", self.abrir_archivo)
        self.tree.bind("<Button-3>", self.mostrar_menu_contextual)
        
        # Frame para barra de progreso
        self.frame_progreso = ttk.Frame(main_frame)
        self.frame_progreso.pack(fill=tk.X, pady=(10, 0))
        
        self.label_progreso = ttk.Label(self.frame_progreso, text="")
        self.label_progreso.pack()
        
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
        """Abre el archivo PDF con el programa predeterminado (doble clic)."""
        ruta = self.obtener_ruta_archivo_seleccionado()
        if ruta and os.path.exists(ruta):
            try:
                os.startfile(ruta)
            except Exception as e:
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
                # Usar explorer con /select para seleccionar el archivo
                subprocess.run(f'explorer /select,"{ruta_windows}"', shell=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la ubicación: {str(e)}")
        elif ruta:
            messagebox.showwarning("Advertencia", "El archivo no existe.")
    
    def validar_archivos(self):
        carpeta = self.carpeta_seleccionada.get()
        
        if not carpeta:
            messagebox.showwarning("Advertencia", "Por favor, seleccione una carpeta primero.")
            return
        
        if not os.path.isdir(carpeta):
            messagebox.showerror("Error", "La carpeta seleccionada no existe.")
            return
        
        # Limpiar resultados anteriores
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Limpiar diccionario de archivos
        self.archivos_dict.clear()
        self.label_resumen.config(text="")
        
        # Obtener lista de archivos PDF
        archivos_pdf = [f for f in os.listdir(carpeta) if f.lower().endswith('.pdf')]
        total_archivos = len(archivos_pdf)
        
        if total_archivos == 0:
            messagebox.showinfo("Información", "No se encontraron archivos PDF en la carpeta seleccionada.")
            return
        
        # Mostrar y configurar barra de progreso
        self.barra_progreso.pack(fill=tk.X, pady=(5, 0))
        self.barra_progreso['maximum'] = total_archivos
        self.barra_progreso['value'] = 0
        
        # Procesar carpeta
        self.root.config(cursor="wait")
        self.root.update()
        
        try:
            self.resultados = []
            correctos = 0
            incorrectos = 0
            
            for i, archivo in enumerate(archivos_pdf):
                # Actualizar barra de progreso
                self.barra_progreso['value'] = i + 1
                self.label_progreso.config(text=f"Procesando: {archivo} ({i + 1}/{total_archivos})")
                self.root.update()
                
                ruta_completa = os.path.join(carpeta, archivo)
                
                # Extraer información del PDF
                info_pdf = extraer_info_pdf(ruta_completa)
                
                if "error" in info_pdf:
                    resultado = {
                        "archivo": archivo,
                        "valido_proveedor": False,
                        "valido_comprobante": False,
                        "mensaje": f"Error al leer PDF: {info_pdf['error']}"
                    }
                else:
                    # Validar archivo
                    resultado = validar_archivo(archivo, info_pdf)
                
                self.resultados.append(resultado)
                
                # Mostrar resultado inmediatamente
                es_valido = resultado["valido_proveedor"] and resultado["valido_comprobante"]
                
                proveedor_texto = "✓" if resultado["valido_proveedor"] else "✗"
                comprobante_texto = "✓" if resultado["valido_comprobante"] else "✗"
                estado_texto = "CORRECTO" if es_valido else "ERROR"
                
                tag = 'ok' if es_valido else 'error'
                
                if es_valido:
                    correctos += 1
                else:
                    incorrectos += 1
                
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
            
            # Ocultar barra de progreso y limpiar texto
            self.barra_progreso.pack_forget()
            self.label_progreso.config(text="")
            
            # Actualizar resumen
            total = len(self.resultados)
            self.label_resumen.config(
                text=f"Total: {total} archivos | ✓ Correctos: {correctos} | ✗ Con errores: {incorrectos}"
            )
            
            if incorrectos > 0:
                messagebox.showinfo(
                    "Validación Completada",
                    f"Se encontraron {incorrectos} archivo(s) con errores de validación.\n"
                    f"Los archivos con errores están resaltados en rojo."
                )
            else:
                messagebox.showinfo(
                    "Validación Completada",
                    f"¡Todos los {total} archivos pasaron la validación correctamente!"
                )
                
        except Exception as e:
            self.barra_progreso.pack_forget()
            self.label_progreso.config(text="")
            messagebox.showerror("Error", f"Error al procesar la carpeta: {str(e)}")
        finally:
            self.root.config(cursor="")


def main():
    root = tk.Tk()
    app = AplicacionValidador(root)
    root.mainloop()


if __name__ == "__main__":
    main()
