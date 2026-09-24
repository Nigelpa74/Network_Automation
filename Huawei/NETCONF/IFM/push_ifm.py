import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <ifm xmlns="urn:huawei:yang:huawei-ifm">
      <interfaces>
        <interface>
          <name>GE0/0/0.300</name>
            <ipv4 xmlns="urn:huawei:yang:huawei-ip">
              <addresses>
            <!-- PASO 1: Eliminar la IP vieja -->
                <address xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                         nc:operation="delete">
                  <ip>10.50.28.2</ip>
                  <mask>255.255.255.128</mask>
                  <type>main</type>
                </address>

            <!-- PASO 2: Agregar la IP nueva -->
                <address xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
                         nc:operation="create">
                  <ip>10.50.28.13</ip>
                  <mask>255.255.255.128</mask>
                  <type>main</type>
                </address>
              </addresses>
            </ipv4>
        </interface>
      </interfaces>
    </ifm>
</config>
"""

# CONFIG_XML = """
# <config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
#     <ifm xmlns="urn:huawei:yang:huawei-ifm">
#       <interfaces>
#         <interface>
#           <name>GE0/0/9.300</name>
#           <description>Test_Netconf</description>
#           <admin-status>up</admin-status>
#           <link-protocol>ethernet</link-protocol>
#           <vrf-name>_public_</vrf-name>
#           <ethernet xmlns="urn:huawei:yang:huawei-ethernet">
#             <l3-sub-interface>
#               <dot1q-termination>
#                 <dot1q-vlans>
#                   <dot1q-vlans>
#                     <vlan-list>300</vlan-list>
#                   </dot1q-vlans>
#                 </dot1q-vlans>
#               </dot1q-termination>
#             </l3-sub-interface>
#           </ethernet>
#           <ipv4 xmlns="urn:huawei:yang:huawei-ip">
#             <addresses>
#               <address>
#                 <ip>172.16.30.2</ip>
#                 <mask>255.255.255.252</mask>
#                 <type>main</type>
#               </address>
#             </addresses>
#           </ipv4>
#         </interface>
#       </interfaces>
#     </ifm>
# </config>
# """

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

def push_ifm(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ IFM aplicado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario-c.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando IFM en {len(routers)} routers...\n")
    for router in routers:
        push_ifm(router)