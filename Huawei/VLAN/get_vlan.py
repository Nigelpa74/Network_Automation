import yaml
import xml.dom.minidom
from ncclient import manager

FILTER = """
<filter type="subtree">
  <vlan xmlns="urn:huawei:yang:huawei-vlan"/>
</filter>
"""

def huawei_connect(router):
    return manager.connect(
        host=router["host"],
        port=int(router["port"]),
        username=router["user"],
        password=router["password"],
        hostkey_verify=False,
        device_params={'name': "huaweiyang"},
        allow_agent=False,
        look_for_keys=False,
        timeout=60
    )

def get_vlan(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            print(f"[{nombre}] Sesion ID: {m._session.id}")

            reply = m.get_config(source="running", filter=FILTER)

            xml_bonito = xml.dom.minidom.parseString(
                str(reply)
            ).toprettyxml(indent="  ")
            xml_bonito = "\n".join(
                line for line in xml_bonito.split("\n") if line.strip()
            )

            print(xml_bonito)

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    for router in routers:
        get_vlan(router)