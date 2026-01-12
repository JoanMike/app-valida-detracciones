# Validador de Detracciones SUNAT

Aplicación de escritorio para validar archivos PDF de constancias de depósito de detracciones emitidas por SUNAT.

## Descripción

Esta herramienta permite validar automáticamente que los nombres de los archivos PDF de detracciones coincidan con la información contenida dentro de cada documento:

1. **Nombre del Proveedor**: Valida que el nombre del proveedor en el archivo coincida con el campo "Nombre/Razón Social del Proveedor" del PDF.
2. **Número de Comprobante**: Valida que el número de comprobante en el nombre del archivo coincida con el campo "Número de Comprobante" del PDF.

## Características

- ✅ Interfaz gráfica intuitiva
- ✅ Procesamiento por lotes de múltiples archivos PDF
- ✅ Barra de progreso en tiempo real
- ✅ Resultados visuales con colores (verde=correcto, rojo=error)
- ✅ Comparación flexible de nombres (ignora acentos, signos, sufijos empresariales)
- ✅ Menú contextual con clic derecho para abrir archivo o ubicación
- ✅ Doble clic para abrir el PDF directamente
- ✅ Soporte para equivalencias especiales personalizables

## Requisitos

- Python 3.8 o superior
- Windows 10/11

## Instalación

1. Clonar o descargar el repositorio:
```bash
git clone <url-del-repositorio>
cd appValidaDetracciones
```

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install pdfplumber
```

## Uso

1. Ejecutar la aplicación:
```bash
python validar_detracciones.py
```

2. Hacer clic en **"Seleccionar Carpeta"** y elegir la carpeta que contiene los PDFs de detracciones.

3. Hacer clic en **"Validar Archivos"** para iniciar la validación.

4. Revisar los resultados:
   - **Verde**: El archivo pasó la validación
   - **Rojo**: El archivo tiene errores de coincidencia

5. Opciones adicionales:
   - **Doble clic**: Abre el PDF con el programa predeterminado
   - **Clic derecho → Abrir archivo**: Abre el PDF
   - **Clic derecho → Abrir ubicación**: Abre el explorador en la ubicación del archivo

## Formato de nombres de archivo esperado

Los archivos PDF deben seguir este formato:
```
{RUC}_{NOMBRE_PROVEEDOR} {NUMERO_COMPROBANTE} DETRACCION.pdf
```

**Ejemplo:**
```
1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION.pdf
```

Donde:
- `1900259454` = Número de referencia/RUC
- `OMNI LOGISTICS (PERU)` = Nombre del proveedor
- `E001-00009926` = Número de comprobante
- `DETRACCION` = Sufijo identificador

## Validaciones flexibles

La aplicación realiza comparaciones inteligentes:

| Nombre en archivo | Nombre en PDF | Resultado |
|-------------------|---------------|-----------|
| KUEHNE NAGEL | KUEHNE + NAGEL S.A. | ✓ Válido |
| ESTUDIO MUNIZ | ESTUDIO MUÑIZ S.R.L. | ✓ Válido |
| MERCADO PAGO PERU | MERCADOPAGO PERU S.R.L. | ✓ Válido |
| TIENDAS POR DPTO RIPLEY | TIENDAS POR DEPARTAMENTO RIPLEY S.A. | ✓ Válido |

## Equivalencias especiales

Para casos donde la validación automática no es posible (nombres muy abreviados), se pueden agregar equivalencias especiales en el diccionario `EQUIVALENCIAS_ESPECIALES` del código:

```python
EQUIVALENCIAS_ESPECIALES = {
    "CONSULT. INTEG. DE MKT Y COMUNIC. NOVACOM": "CONSULTORA INTEGRAL DE MARKETING Y",
}
```

## Estructura del proyecto

```
appValidaDetracciones/
├── validar_detracciones.py    # Aplicación principal
├── README.md                   # Este archivo
├── .gitignore                  # Archivos ignorados por Git
├── venv/                       # Entorno virtual (no incluido en Git)
└── example/                    # Carpeta de ejemplos
    └── *.pdf                   # Archivos PDF de ejemplo
```

## Dependencias

- [pdfplumber](https://github.com/jsvine/pdfplumber) - Extracción de texto de PDFs
- tkinter - Interfaz gráfica (incluido en Python)

## Licencia

Uso interno - Todos los derechos reservados.

## Autor

Desarrollado para la validación de documentos de detracciones SUNAT.
