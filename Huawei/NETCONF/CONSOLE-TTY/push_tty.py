import yaml
from ncclient import manager

#The password is a string ranging from 8 to 16 characters for a plaintext password
CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <tty xmlns="urn:huawei:yang:huawei-tty">
      <console>
        <idle-time-out-min>30</idle-time-out-min>
        <idle-time-out-sec>1</idle-time-out-sec>
        <auth-mode>password</auth-mode>
        <auth-password>Admin@1234</auth-password>
      </console>
  </tty>
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

def push_tty(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ TTY aplicado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando TTY en {len(routers)} routers...\n")
    for router in routers:
        push_tty(router)