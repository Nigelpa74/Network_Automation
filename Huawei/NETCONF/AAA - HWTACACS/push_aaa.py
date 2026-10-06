import yaml
from ncclient import manager

CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <aaa xmlns="urn:huawei:yang:huawei-aaa">
      <lam>
        <users>
          <user>
            <name>netconfv2</name>
            <state>active</state>
            <password-type>irreversible-cipher</password-type>
            <password>CITROENsurvolt18.huawei</password>
            <level>2</level>
            <ftp-dir>flash:/</ftp-dir>
            <ftp-dir-access>read-write-execute</ftp-dir-access>
            <service-terminal>true</service-terminal>
            <service-telnet>false</service-telnet>
            <service-ftp>false</service-ftp>
            <service-ssh>true</service-ssh>
            <service-http>true</service-http>
            <max-access-num>4294967295</max-access-num>
            <password-force-change>false</password-force-change>
          </user>
        </users>
      </lam>
    </aaa>
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

def push_aaa(router):
    nombre = router["nombre"]
    try:
        with huawei_connect(router) as m:
            reply = m.edit_config(
                target="candidate",
                config=CONFIG_XML,
                error_option="rollback-on-error"
            )
            m.commit()
            print(f"[{nombre}] ✅ AAA aplicado correctamente")
    except Exception as e:
        print(f"[{nombre}] ❌ Error: {e}")

def cargar_inventario(archivo="inventario.yml"):
    with open(archivo) as f:
        data = yaml.safe_load(f)
    return data["routers"]

if __name__ == '__main__':
    routers = cargar_inventario()
    print(f"Aplicando AAA en {len(routers)} routers...\n")
    for router in routers:
        push_aaa(router)