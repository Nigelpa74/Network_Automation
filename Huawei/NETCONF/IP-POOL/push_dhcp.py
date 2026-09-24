import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <dhcp xmlns="urn:huawei:yang:huawei-dhcp">
      <common>
        <global>
          <enable>true</enable>
        </global>
      </common>
      <server>
        <global-ip-pools>
          <global-ip-pool>
            <ip-pool-name>pool_vlan30</ip-pool-name>
            <vpn-instance>_public_</vpn-instance>
            <network-ipv4-address>192.168.30.0</network-ipv4-address>
            <network-mask>255.255.255.0</network-mask>
            <gateway-lists>
              <gateway-list>
                <gateway-ip>192.168.30.1</gateway-ip>
              </gateway-list>
            </gateway-lists>
            <lease-time>
              <day>1</day>
              <hour>0</hour>
              <minute>0</minute>
              <unlimited>false</unlimited>
            </lease-time>
            <dns-lists>
              <dns-list>
                <dns-ip>1.1.1.1</dns-ip>
              </dns-list>
              <dns-list>
                <dns-ip>1.1.0.0</dns-ip>
              </dns-list>
            </dns-lists>
            <alarm-ip-used>
              <resum-percent>50</resum-percent>
              <alarm-percent>100</alarm-percent>
            </alarm-ip-used>
            <auto-recycle>
              <day>0</day>
              <hour>0</hour>
              <minute>0</minute>
            </auto-recycle>
          </global-ip-pool>
        </global-ip-pools>
      </server>
    </dhcp>
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

def push_dhcp(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ DHCP aplicado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando DHCP en {len(routers)} routers...\n")
    for router in routers:
        push_dhcp(router)