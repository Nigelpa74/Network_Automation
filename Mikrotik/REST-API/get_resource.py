"""
Prueba simple: GET a la REST API de MikroTik (RouterOS v7+), validando
el certificado del router contra tu CA interna (la que exportaste del
propio MikroTik).

Requisitos:
    pip install requests

Antes de correr, ajusta las 4 variables de abajo.
"""

import json
import requests
from requests.auth import HTTPBasicAuth

HOST = "10.50.22.254"                 # IP de gestión del MikroTik
USER = "MktGlobalfiber"
PASSWORD = r"@\5H\R9%%:9bBxJ"
CA_CERT = r"C:\Users\Nigel\Documents\Ansible\Mikrotik\REST-API\cert_export_minedu-mikrotik-ca.crt.crt"  # ajusta a tu ruta real

# /rest/system/resource es un endpoint de solo lectura, bueno para probar
# conectividad + auth + TLS sin riesgo de tocar configuración.
URL = f"https://{HOST}/rest/system/resource"

try:
    resp = requests.get(
        URL,
        auth=HTTPBasicAuth(USER, PASSWORD),
        verify=CA_CERT,   # valida la cadena de certificado contra tu CA
        timeout=10,
    )
    resp.raise_for_status()
    print(f"Status: {resp.status_code}\n")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

except requests.exceptions.SSLError as e:
    print("❌ Error de validación TLS — revisa que CA_CERT apunte al .pem correcto")
    print(f"   Detalle: {e}")

except requests.exceptions.HTTPError as e:
    print(f"❌ El servidor respondió con error HTTP: {resp.status_code}")
    print(f"   Cuerpo: {resp.text}")

except requests.exceptions.RequestException as e:
    print(f"❌ Error de conexión: {e}")