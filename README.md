# Validador de Detracciones SUNAT

Aplicación de escritorio para validar archivos PDF de constancias de depósito de detracciones emitidas por SUNAT.

<div align="center">
	<img width="678" height="476" alt="detracciones_validator" src="https://github.com/user-attachments/assets/d7ca0a75-853f-491c-9aa5-77a14d173791" />
</div>

## Descripción

Esta herramienta permite validar automáticamente que los nombres de los archivos PDF de detracciones coincidan con la información contenida dentro de cada documento:

1. **Nombre del Proveedor**: Valida que el nombre del proveedor en el archivo coincida con el campo "Nombre/Razón Social del Proveedor" del PDF.
2. **Número de Comprobante**: Valida que el número de comprobante en el nombre del archivo coincida con el campo "Número de Comprobante" del PDF.

## Características

- ✅ Interfaz gráfica intuitiva
- ✅ Procesamiento por lotes de múltiples archivos PDF en segundo plano (la interfaz no se congela)
- ✅ Barra de progreso en tiempo real
- ✅ Resultados visuales con colores (verde=correcto, rojo=error)
- ✅ Comparación flexible de nombres (ignora acentos, signos, sufijos empresariales)
- ✅ Menú contextual con clic derecho para abrir archivo o ubicación
- ✅ Doble clic o tecla Enter para abrir el PDF directamente
- ✅ Soporte para equivalencias especiales personalizables (`equivalencias.json`)
- ✅ Registro de eventos y errores en `validador.log`

## Requisitos

- Python 3.10 o superior
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
pip install -r requirements.txt
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
   - En las columnas de validación: **✓** válido, **✗** no coincide, **—** el dato no se pudo extraer del PDF

5. Opciones adicionales:
   - **Doble clic o Enter**: Abre el PDF con el programa predeterminado
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

**Nota:** cuando la comparación es por palabras significativas, se exige que la mayoría (≥60%) de las palabras largas del nombre del archivo aparezcan en el PDF. Una sola palabra genérica en común (ej. "SERVICIOS") ya no es suficiente para considerar válido un archivo.

## Equivalencias especiales

Para casos donde la validación automática no es posible (nombres muy abreviados), se pueden agregar equivalencias especiales en el archivo `equivalencias.json` (junto al script), sin tocar el código:

```json
{
    "CONSULT. INTEG. DE MKT Y COMUNIC. NOVACOM": "CONSULTORA INTEGRAL DE MARKETING Y"
}
```

- **Clave**: nombre en el archivo (se normaliza en mayúsculas)
- **Valor**: texto que debe aparecer en el PDF para considerarlo válido

Si el archivo no existe o es inválido, la aplicación funciona normalmente sin equivalencias (se registra en `validador.log`).

## Pruebas

La lógica de validación (normalización y comparación de nombres y comprobantes) tiene pruebas unitarias con pytest:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Estructura del proyecto

```
appValidaDetracciones/
├── validar_detracciones.py    # Aplicación principal
├── equivalencias.json         # Equivalencias especiales de nombres (editable)
├── requirements.txt           # Dependencias de producción
├── requirements-dev.txt       # Dependencias de desarrollo (tests)
├── tests/                     # Pruebas unitarias
├── README.md                  # Este archivo
├── LICENSE                    # Términos de uso
├── .gitignore                 # Archivos ignorados por Git
├── validador.log              # Registro de eventos (generado, no versionado)
└── venv/                      # Entorno virtual (no incluido en Git)
```

## Dependencias

- [pdfplumber](https://github.com/jsvine/pdfplumber) - Extracción de texto de PDFs
- tkinter - Interfaz gráfica (incluido en Python)
- [pytest](https://docs.pytest.org/) - Pruebas unitarias (solo desarrollo)

## Licencia

Uso interno - Todos los derechos reservados. Ver archivo `LICENSE`.

## Autor

Desarrollado para la validación de documentos de detracciones SUNAT.
