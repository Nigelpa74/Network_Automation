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
              <peer nc:operation="merge"
                    xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
                <address>10.50.13.26</address>
                <remote-as>101</remote-as>
                <group-name>eBGP_MINEDU_500</group-name>
                <description>CID258795_747278_YURIMAGUAS</description>
                <afs>
                  <af>
                    <type>ipv4uni</type>
                    <ipv4-unicast>
                      <group-name>eBGP_MINEDU_500</group-name>
                    </ipv4-unicast>
                  </af>
                </afs>
              </peer>
            </peers>
          </base-process>
        </bgp>
      </instance>
    </instances>
  </network-instance>
  <!--division -->
  <ifm xmlns="urn:huawei:yang:huawei-ifm">
      <interfaces>
        <interface>
          <name>10GE1/0/7</name>
          <description>CID258795_747278_YURIMAGUAS</description>
          <admin-status>up</admin-status>
          <vrf-name>101</vrf-name>
          <l2-mode-enable>false</l2-mode-enable>
          <ethernet xmlns="urn:huawei:yang:huawei-ethernet">
            <main-interface>
              <l2-mode>disable</l2-mode>
            </main-interface>
          </ethernet>
          <ipv4 xmlns="urn:huawei:yang:huawei-ip">
            <addresses>
              <address>
                <ip>10.50.13.25</ip>
                <mask>255.255.255.252</mask>
                <type>main</type>
              </address>
            </addresses>
          </ipv4>
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

def push_network_instance(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ Instancia de red aplicada correctamente")
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
        push_network_instance(router)