"""
Lectura de TACACS+ en la OLT/router ZTE por NETCONF (modulo zxr10-tacplus, rev 2020-07-22).

Genera por equipo:
  <nombre>_tacplus_config.xml  -> /configuration/tacplus  (datos de configuracion, get-config sobre running)
  <nombre>_tacplus_state.xml   -> /state/tacplus          (datos de estado, config false: solo con <get>)

Las claves compartidas (nodos 'key') se enmascaran al guardar. Pon MASK_KEYS = False
solo si de verdad necesitas verlas, y trata el archivo resultante como secreto.

Inventario: inventario-m.yml (campos por equipo: nombre, host, port, user, password)
"""
import yaml
from lxml import etree
from ncclient import manager

NS = "http://www.zte.com.cn/zxr10/netconf/schema/rosng/tacplus"
MASK_KEYS = True

# Un nodo vacio en un subtree filter selecciona todo su contenido.
CONFIG_FILTER = ("subtree", f'<configuration xmlns="{NS}"></configuration>')
STATE_FILTER = ("subtree", f'<state xmlns="{NS}"></state>')


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
    raiz = etree.fromstring(reply_xml.encode("utf-8"))
    if enmascarar:
        for el in raiz.iter():
            if isinstance(el.tag, str) and etree.QName(el).localname == "key":
                el.text = "***"
    etree.indent(raiz, space="  ")
    return etree.tostring(raiz, pretty_print=True, encoding="unicode")


def guardar(nombre, sufijo, reply):
    archivo = f"{nombre}_cgn_{sufijo}.xml"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(a_xml_bonito(reply.xml, MASK_KEYS))
    print(f"[{nombre}] OK -> {archivo}")


def leer_cgn(r):
    nombre = r["nombre"]
    try:
        with conectar(r) as m:
            print(f"[{nombre}] sesion {m.session_id}")
            # Configuracion: get-config sobre running (la OLT anuncia writable-running)
            guardar(nombre, "config", m.get_config(source="running", filter=CONFIG_FILTER))
            # Estado (config false): solo accesible con <get>, no con get-config
            guardar(nombre, "state", m.get(filter=STATE_FILTER))
    except Exception as e:
        print(f"[{nombre}] Error: {e}")


def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["routers"]


if __name__ == "__main__":
    for router in cargar_inventario():
        leer_tacplus(router)