import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <dns xmlns="urn:huawei:yang:huawei-dns">
    <global>
        <enable>true</enable>
        <server-algorithm>auto</server-algorithm>
    </global>
    <ipv4-servers>
        <ipv4-server xc:operation="remove">
            <vpn>_public_</vpn>
            <address>1.1.1.3</address>
        </ipv4-server>
        <ipv4-server xc:operation="remove">
            <vpn>_public_</vpn>
            <address>8.8.8.8</address>
        </ipv4-server>
        <ipv4-server>
            <vpn>_public_</vpn>
            <address>10.50.2.5</address>
        </ipv4-server>
    </ipv4-servers>
  </dns>
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

def push_dns(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ DNS aplicado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando DNS en {len(routers)} routers...\n")
    for router in routers:
        push_dns(router)