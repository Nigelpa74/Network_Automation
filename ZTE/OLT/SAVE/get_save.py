"""
Lectura flexible y segura de NETCONF para OLTs / Routers ZTE (ROSNG).
Combina filtros XML limpios (estilo Huawei) con enmascaramiento de claves
y separacion de datastores (get-config sobre running vs get para estado).

Inventario: inventario-m.yml (campos: nombre, host, port, user, password)
"""

import yaml
from lxml import etree
from ncclient import manager

MASK_KEYS = True

# -----------------------------------------------------------------------------
# DEFINICIÓN DE FILTROS XML
# Puedes escribir etiquetas exactas, filtrar listas o incluir multiples namespaces.
# -----------------------------------------------------------------------------

# Filtro para Configuración (nodos config true)
FILTER_CONFIG = """
<filter type="subtree">
  <configuration xmlns="http://www.zte.com.cn/zxr10/netconf/schema/rosng/system-manage">
    <auto-save/>
    <timestamp/>
    <multi-user/>
  </configuration>
</filter>
"""

# Filtro para Estado Operacional (nodos config false, consultables solo con <get>)
FILTER_STATE = """
<filter type="subtree">
  <state xmlns="http://www.zte.com.cn/zxr10/netconf/schema/rosng/system-manage">
    <logic-modes/>
  </state>
</filter>
"""


def conectar(r):
    return manager.connect(
        host=r["host"],
        port=int(r["port"]),
        username=r["user"],
        password=r["password"],
        hostkey_verify=False,
        allow_agent=False,
        look_for_keys=False,
        timeout=30,
    )


def a_xml_bonito(reply_xml, enmascarar=True):
    """Parsea el XML, enmascara etiquetas sensibles 'key' e indenta el resultado."""
    raiz = etree.fromstring(reply_xml.encode("utf-8"))
    if enmascarar:
        for el in raiz.iter():
            if isinstance(el.tag, str) and etree.QName(el).localname in ["key", "password", "encrypted-password"]:
                # Preserva indicativo si no hay valor
                if el.text and el.text.strip():
                    el.text = "***"
    etree.indent(raiz, space="  ")
    return etree.tostring(raiz, pretty_print=True, encoding="unicode")


def guardar(nombre, sufijo, reply):
    archivo = f"{nombre}_system_{sufijo}.xml"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(a_xml_bonito(reply.xml, MASK_KEYS))
    print(f"[{nombre}] OK -> {archivo}")


def leer_equipo(r):
    nombre = r["nombre"]
    try:
        with conectar(r) as m:
            print(f"[{nombre}] Sesion NETCONF ID: {m.session_id}")

            # 1. Obtener Configuración (get-config running)
            if FILTER_CONFIG.strip():
                reply_cfg = m.get_config(source="running", filter=FILTER_CONFIG)
                guardar(nombre, "config", reply_cfg)

            # 2. Obtener Estado Operacional (get)
            if FILTER_STATE.strip():
                reply_state = m.get(filter=FILTER_STATE)
                guardar(nombre, "state", reply_state)

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")


def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["routers"]


if __name__ == "__main__":
    for router in cargar_inventario():
        leer_equipo(router)