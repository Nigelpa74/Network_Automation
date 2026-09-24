import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <ifm xmlns="urn:huawei:yang:huawei-ifm">
      <interfaces>
        <interface xc:operation="remove">
          <name>GE0/0/9.300</name>
        </interface>
        <interface xc:operation="remove">
          <name>GE0/0/4</name>
        </interface>
      </interfaces>
    </ifm>
</config>
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

def delete_ifm(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ IFM eliminado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Eliminando IFM en {len(routers)} routers...\n")
    for router in routers:
        delete_ifm(router)