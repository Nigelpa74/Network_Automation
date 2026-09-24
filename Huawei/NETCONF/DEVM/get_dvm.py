import os
import yaml
import xml.dom.minidom
from ncclient import manager

FILTER = """
<filter type="subtree">
  <devm xmlns="urn:huawei:yang:huawei-devm">
    <ports>
      <port>
        <position>GE0/0/8</position>
        <admin-state/>
        <optical-module xmlns="urn:huawei:yang:huawei-pic">
          <vendor-pn/>
          <wavelength/>
          <transmission-distance/>
          <manufacture-date/>
          <serial-number/>
        </optical-module>
      </port>
      <port>
        <position>GE0/0/9</position>
        <admin-state/>
        <optical-module xmlns="urn:huawei:yang:huawei-pic">
          <vendor-pn/>
          <wavelength/>
          <transmission-distance/>
          <manufacture-date/>
          <serial-number/>
        </optical-module>
      </port>
    </ports>
  </devm>
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
        timeout=20
    )

def get_devm(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            print(f"[{nombre}] Sesion ID: {m._session.id}")

            reply = m.get(filter=FILTER)

            xml_bonito = xml.dom.minidom.parseString(
                str(reply)
            ).toprettyxml(indent="  ")
            xml_bonito = "\n".join(
                line for line in xml_bonito.split("\n") if line.strip()
            )

            #os.makedirs("outputs", exist_ok=True)
            archivo = f"{nombre}_devm.xml"
            #archivo = f"outputs/{nombre}_devm.xml"
            with open(archivo, "w") as f:
                f.write(xml_bonito)

            print(f"[{nombre}] ✅ Guardado en {archivo}")

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario-c.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    for router in routers:
        get_devm(router)