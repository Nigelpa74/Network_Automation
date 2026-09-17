import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <vty xmlns="urn:huawei:yang:huawei-vty">
    <lines>
      <line>
        <index>54</index>
        <idle-timeout-min>10</idle-timeout-min>
        <idle-timeout-sec>0</idle-timeout-sec>
        <auth-mode>aaa</auth-mode>
        <privilege-level>0</privilege-level>
        <history-cmd-size>10</history-cmd-size>
        <screen-length>24</screen-length>
        <shell-enable>true</shell-enable>
        <proto-inbound>ssh</proto-inbound>
      </line>
    </lines>
  </vty>
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

def push_vty(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ VTY aplicado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando VTY en {len(routers)} routers...\n")
    for router in routers:
        push_vty(router)