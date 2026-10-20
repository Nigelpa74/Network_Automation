import sys
import yaml
from lxml import etree
from ncclient import manager

# =============================================================================
# PARÁMETROS DE CONFIGURACIÓN
# =============================================================================
DRY_RUN = False               # True: solo imprime el XML sin conectarse al equipo
AUTO_CONFIRM = True         # True: Confirma automáticamente en todos los equipos sin preguntar
TIMEOUT_CONFIRMACION = 120   # Segundos antes de aplicar rollback automático en la OLT
GUARDAR_STARTUP = True      # True: Copia de running a startup (persistencia) tras confirmar
USAR_CAPS_ZTE = True         # True: Anuncia las capabilities requeridas por ROSNG de ZTE

# =============================================================================
# PAYLOAD XML MODULAR (Puedes agregar o quitar múltiples bloques/módulos aquí)
# =============================================================================
CONFIG_XML = """
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  
  <!-- Módulo 1: Gestión de Usuarios (adm-mgr) -->
  <configuration xmlns="http://www.zte.com.cn/zxr10/netconf/schema/rosng/adm-mgr">
    <adm-mgr>
      <usernames>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>aoncebay</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>sartica</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>rsanchez</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>operador.global</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>wjesus</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>jhuaman</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>jmoreno</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>yhuatuco</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>gcahuana</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>amendez</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username>        
        <username xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="merge">
          <name>acuba</name>
          <bind-authen-template>2</bind-authen-template>
          <bind-author-template>3</bind-author-template>
        </username> 
      </usernames>
    </adm-mgr>
  </configuration>

  <!-- Módulo 2: Guardado automático u otros módulos (Ejemplo system-manage) -->
  <!-- 
  <configuration xmlns="http://www.zte.com.cn/zxr10/netconf/schema/rosng/system-manage">
    <system-manage>
      ...
    </system-manage>
  </configuration>
  -->

</config>
"""

# # RPC opcional en caso de que copy_config falle y se requiera invocar la acción directa de save
# SAVE_ACTION_RPC = """
# <action xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
#   <operation xmlns="http://www.zte.com.cn/zxr10/netconf/schema/rosng/system-manage">
#     <system-manage>
#       <save-configuration>
#         <target>
#           <txt/>
#         </target>
#       </save-configuration>
#     </system-manage>
#   </operation>
# </action>
# """

# Namespaces y Capabilities requeridas por ZTE ROSNG
NS_ADM = "http://www.zte.com.cn/zxr10/netconf/schema/rosng/adm-mgr"
NS_NC = "urn:ietf:params:xml:ns:netconf:base:1.0"
CAPS_ZTE = [
    "http://www.zte.com.cn/zxr10/netconf/capabilities/error-params1.0",
    "http://www.zte.com.cn/zxr10/netconf/capabilities/merge-replace1.0",
]


def filtro_verificacion_general():
    """Genera un filtro subtree para traer todos los usuarios y verificar el bloque completo."""
    return (
        "subtree",
        f'<configuration xmlns="{NS_ADM}"><adm-mgr><usernames/></adm-mgr></configuration>',
    )


def conectar(r):
    """Establece conexión NETCONF con las capabilities de ZTE."""
    return manager.connect(
        host=r["host"],
        port=int(r["port"]),
        username=r["user"],
        password=r["password"],
        hostkey_verify=False,
        allow_agent=False,
        look_for_keys=False,
        timeout=60,
        nc_params={"capabilities": CAPS_ZTE} if USAR_CAPS_ZTE else {},
    )


def guardar_persistencia(m, nombre):
    """Ejecuta el guardado en startup-config usando copy_config o RPC de respaldo."""
    print(f"[{nombre}] Guardando configuración en startup (persistencia)...")
    try:
        # Método 1: Estándar NETCONF copy_config
        m.copy_config(source="running", target="startup")
        print(f"[{nombre}] ✅ Configuración running copiada exitosamente a startup (copy-config).")
    except Exception as e:
        print(f"[{nombre}] ⚠️ copy-config no soportado o falló ({e}). Intentando vía RPC Action...")
        # try:
        #     # Método 2: Accion RPC propia de ZTE ROSNG
        #     m.dispatch(SAVE_ACTION_RPC)
        #     print(f"[{nombre}] ✅ Guardado en startup ejecutado mediante RPC save-configuration.")
        # except Exception as rpc_err:
        #     print(f"[{nombre}] ❌ Error al guardar en startup: {rpc_err}")


def aplicar_push_y_guardar(r):
    nombre = r["nombre"]
    
    # Formatear el XML para impresión limpia
    xml_pretty = etree.tostring(etree.fromstring(CONFIG_XML), pretty_print=True).decode()
    print(f"\n[{nombre}] XML a enviar:\n{xml_pretty}")
    
    if DRY_RUN:
        print(f"[{nombre}] DRY_RUN activo: no se envía nada al equipo.")
        return

    with conectar(r) as m:
        # Validar capabilities requeridas del servidor
        caps_servidor = " ".join(m.server_capabilities)
        for req in ("capability:candidate", "capability:confirmed-commit"):
            if req not in caps_servidor:
                sys.exit(f"[{nombre}] El equipo no anuncia {req}; abortando.")

        # Flujo seguro transaccional en Candidate
        with m.locked("candidate"):
            try:
                print(f"[{nombre}] Aplicando edit-config en candidate...")
                m.edit_config(
                    target="candidate",
                    config=CONFIG_XML,
                    default_operation="merge",
                    error_option="rollback-on-error"
                )
            except Exception as e:
                m.discard_changes()
                print(f"[{nombre}] ❌ edit-config falló, candidate descartado: {e}")
                return

            # Commit confirmado con temporizador
            m.commit(confirmed=True, timeout=str(TIMEOUT_CONFIRMACION))
            print(f"[{nombre}] ⏳ Commit confirmado aplicado. Tienes {TIMEOUT_CONFIRMACION}s para verificar.")

            # Verificación del estado general en running (muestra todos los usuarios)
            try:
                ver = m.get_config(source="running", filter=filtro_verificacion_general())
                print(f"[{nombre}] Resultado actual en running (Usuarios):")
                print(etree.tostring(etree.fromstring(ver.xml.encode()), pretty_print=True).decode())
            except Exception as e:
                print(f"[{nombre}] No se pudo obtener la verificación general: {e}")

            # Confirmación interactiva del operador
            confirmacion = input("Confirmar el cambio de forma definitiva? [s/N]: ").strip().lower()
            if AUTO_CONFIRM:
                confirmacion = "s"
                print(f"[{nombre}] AUTO_CONFIRM habilitado: confirmando automáticamente...")
            else:
                confirmacion = input(f"[{nombre}] Confirmar el cambio de forma definitiva? [s/N]: ").strip().lower()

            if confirmacion == "s":
                m.commit()
                print(f"[{nombre}] ✅ Cambio confirmado definitivamente.")
                
                # Guardar en startup si está habilitado
                if GUARDAR_STARTUP:
                    guardar_persistencia(m, nombre)
            else:
                m.cancel_confirm()
                print(f"[{nombre}] 🔄 Cambio cancelado; la OLT revierte al estado anterior.")


def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["routers"]


if __name__ == "__main__":
    for router in cargar_inventario():
        try:
            aplicar_push_y_guardar(router)
        except Exception as e:
            print(f"[{router.get('nombre', 'DESCONOCIDO')}] Error durante el proceso: {e}")