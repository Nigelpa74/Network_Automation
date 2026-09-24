import yaml
from ncclient import manager

CONFIG_XML = """
    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <network-instance xmlns="urn:huawei:yang:huawei-network-instance">
        <instances>
          <instance>
            <name>101</name>
            <bgp xmlns="urn:huawei:yang:huawei-bgp">
              <base-process>
                <peers>
                  <peer xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                        nc:operation="remove">
                    <address>10.50.22.126</address>
                  </peer>
                </peers>
              </base-process>
            </bgp>
          </instance>
        </instances>
      </network-instance>
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

def delete_network_instance(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ Instancia de red eliminada correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando instancia de red en {len(routers)} routers...\n")
    for router in routers:
        delete_network_instance(router)