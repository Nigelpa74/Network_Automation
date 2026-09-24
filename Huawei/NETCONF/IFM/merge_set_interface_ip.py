# test_set_interface_ip.py
import sys
from ncclient import manager

# Solo el contenido del <config> — ncclient agrega el <rpc> automáticamente
CONFIG_XML = """
<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
   <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0">
     <name>GE0/0/0</name>
     <type xmlns:iana="urn:ietf:params:xml:ns:yang:iana-if-type">iana:ethernetCsmacd</type>
     <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip" xc:operation="merge"> 
      <address>
       <ip>192.168.150.202</ip>
       <prefix-length>24</prefix-length>
      </address>
      <mtu>1200</mtu>
     </ipv4>
    </interface>
   </interfaces>
  </config>
"""

def huawei_connect(host, port, user, password):
    return manager.connect(
        host=host,
        port=int(port),
        username=user,
        password=password,
        hostkey_verify=False,
        device_params={'name': "huaweiyang"},
        allow_agent=False,
        look_for_keys=False,
        timeout=60
    )

def set_interface_ip(host, port, user, password):
    with huawei_connect(host, port, user, password) as m:
        print(f"Sesion ID: {m._session.id}")

        # edit-config sobre candidate y luego commit
        reply = m.edit_config(
            target="candidate",
            config=CONFIG_XML,
            error_option="rollback-on-error"
        )
        print(f"edit-config reply: {reply}")

        # Confirmar cambios
        commit_reply = m.commit()
        print(f"commit reply: {commit_reply}")
        print("Configuracion aplicada correctamente")

if __name__ == '__main__':
    set_interface_ip(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])