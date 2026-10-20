"""
Crear o eliminar un usuario "declarado" en la OLT ZTE por NETCONF (modulo zxr10-adm-mgr).

Flujo seguro (la OLT anuncia candidate + confirmed-commit; este script no usa validate):
  1. lock del datastore candidate
  2. edit-config sobre candidate (rollback-on-error)
  3. commit confirmado con temporizador: si no confirmas, la OLT revierte sola
  4. get-config de running para verificar
  5. confirmas (commit) o cancelas (cancel-commit)
  6. unlock

DRY_RUN = True (por defecto): solo imprime el XML que enviaria, no se conecta.
Usa en el inventario un usuario con permisos de ESCRITURA (por ejemplo uno declarado con
authorization-template de nivel 15). Un usuario en solo lectura no podra aplicar cambios.

Inventario: inventario-m.yml (campos por equipo: nombre, host, port, user, password)
"""
import sys
import yaml
from lxml import etree
from ncclient import manager

# ---------------------------- Parametros ----------------------------
DRY_RUN = False              # Cambiar a False solo cuando el XML impreso te convenza
ACCION = "crear"            # "crear" o "eliminar"
USUARIO = "sartica"  # nombre (1-65 caracteres; tu politica pide minimo 3)
AUTHEN_TEMPLATE = 2         # authentication-template 2 -> TACACS+
AUTHOR_TEMPLATE = 3         # authorization-template 3 -> nivel 15, escritura
TIMEOUT_CONFIRMACION = 120  # segundos antes del rollback automatico
GUARDAR_STARTUP = False     # True: copia running -> startup despues de confirmar
USAR_CAPS_ZTE = True        # True: el cliente anuncia en su <hello> capabilities propias de ZTE
# --------------------------------------------------------------------

NS_ADM = "http://www.zte.com.cn/zxr10/netconf/schema/rosng/adm-mgr"
NS_NC = "urn:ietf:params:xml:ns:netconf:base:1.0"
# Copiadas tal cual de las que anuncia la OLT (sin ":" antes de 1.0)
CAPS_ZTE = [
    "http://www.zte.com.cn/zxr10/netconf/capabilities/error-params1.0",
    "http://www.zte.com.cn/zxr10/netconf/capabilities/merge-replace1.0",
]


def construir_config():
    if ACCION == "crear":
        usuario = (
            f"<username>"
            f"<name>{USUARIO}</name>"
            f"<bind-authen-template>{AUTHEN_TEMPLATE}</bind-authen-template>"
            f"<bind-author-template>{AUTHOR_TEMPLATE}</bind-author-template>"
            f"</username>"
        )
    elif ACCION == "eliminar":
        usuario = (
            f'<username xmlns:nc="{NS_NC}" nc:operation="delete">'
            f"<name>{USUARIO}</name>"
            f"</username>"
        )
    else:
        sys.exit("ACCION debe ser 'crear' o 'eliminar'")
    return (
        f'<config xmlns="{NS_NC}">'
        f'<configuration xmlns="{NS_ADM}"><adm-mgr><usernames>{usuario}</usernames></adm-mgr></configuration>'
        f"</config>"
    )


# Mismo nodo, solo para verificar despues del cambio (sin traer contrasenas de otros usuarios)
def filtro_verificacion():
    return (
        "subtree",
        f'<configuration xmlns="{NS_ADM}"><adm-mgr><usernames>'
        f"<username><name>{USUARIO}</name></username>"
        f"</usernames></adm-mgr></configuration>",
    )


def conectar(r):
    return manager.connect(
        host=r["host"], port=int(r["port"]), username=r["user"], password=r["password"],
        hostkey_verify=False, allow_agent=False, look_for_keys=False, timeout=60,
        nc_params={"capabilities": CAPS_ZTE} if USAR_CAPS_ZTE else {},
    )


def aplicar(r):
    nombre = r["nombre"]
    config = construir_config()
    print(f"[{nombre}] XML a enviar:\n{etree.tostring(etree.fromstring(config), pretty_print=True).decode()}")
    if DRY_RUN:
        print(f"[{nombre}] DRY_RUN activo: no se envio nada.")
        return

    with conectar(r) as m:
        caps = " ".join(m.server_capabilities)
        for requerida in ("capability:candidate", "capability:confirmed-commit"):
            if requerida not in caps:
                sys.exit(f"[{nombre}] El equipo no anuncia {requerida}; abortando.")

        with m.locked("candidate"):
            try:
                m.edit_config(target="candidate", config=config,
                              default_operation="merge", error_option="rollback-on-error")
            except Exception as e:
                m.discard_changes()
                print(f"[{nombre}] edit-config fallo, candidate descartado: {e}")
                return

            m.commit(confirmed=True, timeout=str(TIMEOUT_CONFIRMACION))
            print(f"[{nombre}] commit confirmado aplicado; tienes {TIMEOUT_CONFIRMACION}s para verificar.")

            ver = m.get_config(source="running", filter=filtro_verificacion())
            print(etree.tostring(etree.fromstring(ver.xml.encode()), pretty_print=True).decode())

            if input("Confirmar el cambio de forma definitiva? [s/N]: ").strip().lower() == "s":
                m.commit()
                print(f"[{nombre}] cambio confirmado.")
                if GUARDAR_STARTUP:
                    m.copy_config(source="running", target="startup")
                    print(f"[{nombre}] running copiado a startup.")
            else:
                m.cancel_commit()
                print(f"[{nombre}] cambio cancelado; la OLT vuelve al estado anterior.")


def cargar_inventario(archivo="inventario-m.yml"):
    with open(archivo, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["routers"]


if __name__ == "__main__":
    for router in cargar_inventario():
        try:
            aplicar(router)
        except Exception as e:
            print(f"[{router['nombre']}] Error: {e}")