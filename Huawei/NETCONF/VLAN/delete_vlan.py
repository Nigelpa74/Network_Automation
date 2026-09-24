import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <vlan xmlns="urn:huawei:yang:huawei-vlan">
    <vlans>
        <vlan xc:operation="remove">
          <id>30</id>
        </vlan>
        <vlan xc:operation="remove">
          <id>40</id>
        </vlan>
    </vlans>
  </vlan>
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

def push_vlan(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ VLAN eliminado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Eliminando VLAN en {len(routers)} routers...\n")
    for router in routers:
        push_vlan(router)