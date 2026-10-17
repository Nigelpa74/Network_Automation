"""
Descubrimiento NETCONF en OLT ZTE: que modelos YANG expone realmente el equipo.

Por cada equipo del inventario genera:
  <nombre>_capabilities.txt   -> capabilities del <hello> (modulos, revisiones, features)
  <nombre>_schemas.xml        -> respuesta de /netconf-state/schemas
  schemas_<nombre>/*.yang     -> todos los schemas descargados con get-schema

Usa el mismo inventario que tu script: inventario-m.yml
(campos por equipo: nombre, host, port, user, password)
"""
import os
import re
import yaml
from lxml import etree
from ncclient import manager

NS_MON = "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"

SCHEMAS_FILTER = f"""
<netconf-state xmlns="{NS_MON}">
  <schemas/>
</netconf-state>
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
        timeout=60,
    )


def seguro(texto):
    return re.sub(r"[^A-Za-z0-9._@-]", "_", texto)


def descubrir(r):
    nombre = r["nombre"]
    with conectar(r) as m:
        print(f"[{nombre}] sesion {m.session_id}")

        # 1) Capabilities del hello
        caps = sorted(m.server_capabilities)
        with open(f"{nombre}_capabilities.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(caps))
        print(f"[{nombre}] {len(caps)} capabilities -> {nombre}_capabilities.txt")

        # 2) Lista de schemas (ietf-netconf-monitoring)
        reply = m.get(filter=("subtree", SCHEMAS_FILTER))
        raiz = etree.fromstring(reply.xml.encode("utf-8"))
        with open(f"{nombre}_schemas.xml", "wb") as f:
            f.write(etree.tostring(raiz, pretty_print=True))

        schemas = []
        for s in raiz.iter(f"{{{NS_MON}}}schema"):
            def val(tag):
                e = s.find(f"{{{NS_MON}}}{tag}")
                return e.text if e is not None else None
            if val("format") in (None, "yang"):
                schemas.append((val("identifier"), val("version")))
        print(f"[{nombre}] {len(schemas)} schemas YANG anunciados")

        # 3) Descargar cada schema con get-schema
        carpeta = f"schemas_{nombre}"
        os.makedirs(carpeta, exist_ok=True)
        for ident, version in schemas:
            try:
                kwargs = {"format": "yang"}
                if version:
                    kwargs["version"] = version
                rep = m.get_schema(ident, **kwargs)
                data = etree.fromstring(rep.xml.encode("utf-8")).find(f"{{{NS_MON}}}data")
                texto = data.text if data is not None else ""
                archivo = os.path.join(carpeta, seguro(f"{ident}@{version or 'sin-version'}") + ".yang")
                with open(archivo, "w", encoding="utf-8") as f:
                    f.write(texto)
                print(f"  ok  {ident}@{version}")
            except Exception as e:
                print(f"  ERR {ident}@{version}: {e}")


def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["routers"]


if __name__ == "__main__":
    for router in cargar_inventario():
        try:
            descubrir(router)
        except Exception as e:
            print(f"[{router['nombre']}] Error: {e}")