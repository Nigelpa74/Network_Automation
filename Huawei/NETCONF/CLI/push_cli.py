import yaml
from ncclient import manager
from ncclient.xml_ import to_ele

BATCH_COMMANDS = """system-view
web-manager enable port 443
web-manager http forward enable
web-manager ipv4 server-source -a 192.168.150.201 vpn-instance public
undo web-manager lock-ip
return
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

def push_cli_batch(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            print(f"[{nombre}] Sesion ID: {m._session.id}")

            rpc = to_ele(f"""
                <execute-batch-commands xmlns="urn:huawei:yang:huawei-cli">
                  <batch-commands>{BATCH_COMMANDS}</batch-commands>
                  <execute-policy>continue-on-error</execute-policy>
                </execute-batch-commands>
            """)
            reply = m.dispatch(rpc)
            print(f"[{nombre}] Resultado:\n{reply}")

    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    for router in routers:
        push_cli_batch(router)