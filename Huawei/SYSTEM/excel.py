import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import pandas as pd

xml_filename = "resultado_inventario_system.xml"
excel_filename = "inventario_uptime.xlsx"

tree = ET.parse(xml_filename)
root = tree.getroot()

# Definir la zona horaria de Perú (UTC-5)
pe_tz = timezone(timedelta(hours=-5))

data = []

for router in root.findall("router"):
    nombre = router.attrib.get("nombre", "")
    host = router.attrib.get("host", "")

    boot_time_raw = ""

    for elem in router.iter():
        clean_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if clean_tag == "boot-time":
            boot_time_raw = elem.text or ""

    boot_time_local_str = ""
    uptime_formateado = ""

    if boot_time_raw:
        # Parsear fecha UTC de NETCONF (ej: 2026-09-17T12:23:18Z)
        dt_utc = datetime.strptime(boot_time_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        
        # 1. Convertir a hora local Perú (UTC-5)
        dt_local = dt_utc.astimezone(pe_tz)
        boot_time_local_str = dt_local.strftime("%d/%m/%Y %H:%M:%S")

        # 2. Calcular Uptime REAL (Hora actual UTC - Boot Time UTC)
        now_utc = datetime.now(timezone.utc)
        uptime_diff = now_utc - dt_utc

        dias = uptime_diff.days
        horas, rem = divmod(uptime_diff.seconds, 3600)
        minutos, _ = divmod(rem, 60)

        uptime_formateado = f"{dias}d {horas}h {minutos}m" if dias > 0 else f"{horas}h {minutos}m"

    data.append({
        "Equipo": nombre,
        "IP / Host": host,
        "Uptime Real": uptime_formateado,
        "Fecha Arranque (Hora Local UTC-5)": boot_time_local_str,
        "Fecha Arranque (UTC NETCONF)": boot_time_raw
    })

df = pd.DataFrame(data)
df.to_excel(excel_filename, index=False)

print("¡Procesado correctamente! Las fechas de arranque ahora coinciden con la CLI.")