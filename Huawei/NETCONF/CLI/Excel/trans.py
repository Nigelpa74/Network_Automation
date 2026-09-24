import pandas as pd

# Cargar el archivo Excel
excel_path = 'Report_SFP.xlsx'
df = pd.read_excel(excel_path)

# Filtrar por colegios P2P y Estado Router 'Activo'
p2p_activos = df[
    (df['TECNOLOGIA DE ACCESO'].str.strip().str.upper() == 'P2P') & 
    (df['ESTADO ROUTER'].str.strip().str.upper() == 'ACTIVO')
]

# Construir la estructura YAML
yaml_content = ["routers:"]

for _, row in p2p_activos.iterrows():
    nombre = int(row['N°'])
    # Limpiar el prefijo /32 de la IP Loopback
    host = str(row['ASIGNACION IP LOOPBACK /32']).replace('/32', '').strip()
    
    entry = (
        f"  - nombre: {nombre}\n"
        f"    host: {host}\n"
        f"    port: 830\n"
        f"    user: AdminGF\n"
        f"    password: HW#*c8Q$Tq9W"
    )
    yaml_content.append(entry)

# Guardar en el archivo final YAML
with open("inventario-c.yml", "w") as f:
    f.write("\n\n".join(yaml_content))

print(f"¡Proceso completado! Se exportaron {len(p2p_activos)} colegios activos a 'inventario-c.yml'.")