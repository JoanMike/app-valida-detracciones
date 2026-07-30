"""
Pruebas unitarias para la lógica de validación de validar_detracciones.py
(funciones puras, sin GUI ni PDFs reales).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validar_detracciones as vd


INFO_PDF_OK = {
    "nombre_proveedor": "OMNI LOGISTICS (PERU) S.A.C.",
    "numero_comprobante": "E001-9926",
    "texto_completo": "",
}


# ---------------------------------------------------------------------------
# quitar_acentos
# ---------------------------------------------------------------------------

def test_quitar_acentos_elimina_diacriticos():
    assert vd.quitar_acentos("MUÑIZ") == "MUNIZ"
    assert vd.quitar_acentos("José Ñandú") == "Jose Nandu"


def test_quitar_acentos_texto_vacio():
    assert vd.quitar_acentos("") == ""
    assert vd.quitar_acentos(None) == ""


# ---------------------------------------------------------------------------
# comparar_nombres_flexible — casos que deben seguir pasando
# ---------------------------------------------------------------------------

def test_comparar_coincidencia_exacta_tras_normalizar():
    valido, _ = vd.comparar_nombres_flexible(
        "OMNI LOGISTICS (PERU)", "OMNI LOGISTICS (PERU) S.A.C."
    )
    assert valido is True


def test_comparar_ignora_acentos():
    valido, _ = vd.comparar_nombres_flexible("ESTUDIO MUNIZ", "ESTUDIO MUÑIZ S.R.L.")
    assert valido is True


def test_comparar_ignora_espacios_y_signos():
    valido, _ = vd.comparar_nombres_flexible("MERCADO PAGO PERU", "MERCADOPAGO PERU S.R.L.")
    assert valido is True
    valido, _ = vd.comparar_nombres_flexible("KUEHNE NAGEL", "KUEHNE + NAGEL S.A.")
    assert valido is True


def test_comparar_palabras_significativas_mayoria():
    # 2 de 3 palabras largas en común (TIENDAS, RIPLEY) -> válido
    valido, _ = vd.comparar_nombres_flexible(
        "TIENDAS POR DPTO RIPLEY", "TIENDAS POR DEPARTAMENTO RIPLEY S.A."
    )
    assert valido is True


def test_comparar_equivalencia_especial():
    valido, _ = vd.comparar_nombres_flexible(
        "CONSULT. INTEG. DE MKT Y COMUNIC. NOVACOM",
        "CONSULTORA INTEGRAL DE MARKETING Y COMUNICACIONES NOVACOM S.A.C.",
    )
    assert valido is True


def test_comparar_nombres_vacios_es_invalido():
    valido, _ = vd.comparar_nombres_flexible("", "ALGO S.A.")
    assert valido is False
    valido, _ = vd.comparar_nombres_flexible("ALGO", None)
    assert valido is False


# ---------------------------------------------------------------------------
# comparar_nombres_flexible — falsos positivos que deben rechazarse
# ---------------------------------------------------------------------------

def test_comparar_rechaza_una_sola_palabra_comun_generica():
    # Solo comparten "GONZALEZ" (1 de 2 palabras largas) -> inválido
    valido, _ = vd.comparar_nombres_flexible(
        "TRANSPORTES GONZALEZ", "INVERSIONES GONZALEZ S.A.C."
    )
    assert valido is False


def test_comparar_rechaza_palabra_comun_de_sector():
    # Solo comparten "SERVICIOS" -> inválido
    valido, _ = vd.comparar_nombres_flexible(
        "SERVICIOS GENERALES", "SERVICIOS TECNICOS LIMA S.A."
    )
    assert valido is False


# ---------------------------------------------------------------------------
# normalizar_numero_comprobante
# ---------------------------------------------------------------------------

def test_normalizar_comprobante_quita_ceros_a_la_izquierda():
    assert vd.normalizar_numero_comprobante("E001-00009926") == "E001-9926"


def test_normalizar_comprobante_quita_espacios_y_mayusculas():
    assert vd.normalizar_numero_comprobante("e001 - 00009926") == "E001-9926"


def test_normalizar_comprobante_vacio():
    assert vd.normalizar_numero_comprobante("") == ""
    assert vd.normalizar_numero_comprobante(None) == ""


# ---------------------------------------------------------------------------
# validar_archivo
# ---------------------------------------------------------------------------

def test_validar_archivo_correcto_con_ceros_de_mas_en_pdf_o_archivo():
    r = vd.validar_archivo(
        "1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION.pdf", INFO_PDF_OK
    )
    assert r["valido_proveedor"] is True
    assert r["valido_comprobante"] is True
    assert r["mensaje"] == "OK"


def test_validar_archivo_usa_el_ultimo_patron_como_comprobante():
    # El proveedor contiene "A1-100"; el comprobante real es el último patrón
    r = vd.validar_archivo(
        "20331234567_EMPRESA A1-100 SERVICIOS E001-00099 DETRACCION.pdf", INFO_PDF_OK
    )
    assert r["comprobante_archivo"] == "E001-00099"


def test_validar_archivo_sin_comprobante_en_nombre():
    r = vd.validar_archivo("ARCHIVO SIN NUMERO.pdf", INFO_PDF_OK)
    assert r["valido_proveedor"] is False
    assert r["valido_comprobante"] is False
    assert r["mensaje"]


def test_validar_archivo_distingue_comprobante_no_extraido():
    info = {"nombre_proveedor": "OMNI LOGISTICS (PERU) S.A.C.",
            "numero_comprobante": None, "texto_completo": ""}
    r = vd.validar_archivo(
        "1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION.pdf", info
    )
    assert r["valido_comprobante"] is False
    assert r.get("comprobante_extraido") is False
    assert "extraer" in r["mensaje"].lower()


def test_validar_archivo_distingue_proveedor_no_extraido():
    info = {"nombre_proveedor": None,
            "numero_comprobante": "E001-00009926", "texto_completo": ""}
    r = vd.validar_archivo(
        "1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION.pdf", info
    )
    assert r["valido_proveedor"] is False
    assert r.get("proveedor_extraido") is False
    assert "extraer" in r["mensaje"].lower()
    # El comprobante sí se extrae y coincide
    assert r["valido_comprobante"] is True


# ---------------------------------------------------------------------------
# cargar_equivalencias (configuración externa)
# ---------------------------------------------------------------------------

def test_cargar_equivalencias_desde_json(tmp_path):
    ruta = tmp_path / "equivalencias.json"
    ruta.write_text(
        json.dumps({"NOMBRE CORTO": "NOMBRE LARGO EN PDF"}), encoding="utf-8"
    )
    equivalencias = vd.cargar_equivalencias(str(ruta))
    assert equivalencias == {"NOMBRE CORTO": "NOMBRE LARGO EN PDF"}


def test_cargar_equivalencias_archivo_inexistente(tmp_path):
    assert vd.cargar_equivalencias(str(tmp_path / "no_existe.json")) == {}


def test_cargar_equivalencias_json_invalido(tmp_path):
    ruta = tmp_path / "equivalencias.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    assert vd.cargar_equivalencias(str(ruta)) == {}
