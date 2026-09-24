import xml.etree.ElementTree as ET
import re
import pandas as pd

def parse_xml_to_excel(xml_file, output_excel):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    data = []

    # Expresiones regulares para capturar CID, interfaz y los parámetros del SFP
    cid_pattern = re.compile(r'<([^>]+)>')
    interface_pattern = re.compile(r'dis interface (\S+) transceiver')
    
    fields = [
        'Wavelength (nm)',
        'Transfer Distance (m)',
        'Vendor Part Number',
        'Manu. Serial Number',
        'Manufacturing Date'
    ]

    for router in root.findall('router'):
        router_nombre = router.get('nombre', '-')
        router_host = router.get('host', '-')

        content_elem = router.find('.//{urn:huawei:yang:huawei-cli}content')
        content_text = content_elem.text if content_elem is not None and content_elem.text else ''

        # Extraer el nombre del colegio/CID
        cid_match = cid_pattern.search(content_text)
        cid_name = cid_match.group(1) if cid_match else '-'

        # Inicializar diccionario para el registro actual
        row = {
            'Router ID': router_nombre,
            'Host IP': router_host,
            'CID / Colegio': cid_name,
            
            # ge0/0/8
            'ge0/0/8_Wavelength': '-',
            'ge0/0/8_Distance': '-',
            'ge0/0/8_PartNumber': '-',
            'ge0/0/8_SerialNumber': '-',
            'ge0/0/8_MfgDate': '-',
            
            # ge0/0/9
            'ge0/0/9_Wavelength': '-',
            'ge0/0/9_Distance': '-',
            'ge0/0/9_PartNumber': '-',
            'ge0/0/9_SerialNumber': '-',
            'ge0/0/9_MfgDate': '-'
        }

        # Dividir el contenido por los comandos ejecutados
        blocks = re.split(r'(?=<[^>]+>dis interface)', content_text)

        for block in blocks:
            if not block.strip():
                continue

            if_match = interface_pattern.search(block)
            if not if_match:
                continue

            interface_name = if_match.group(1).lower()

            prefix = None
            if 'ge0/0/8' in interface_name:
                prefix = 'ge0/0/8'
            elif 'ge0/0/9' in interface_name:
                prefix = 'ge0/0/9'

            if prefix:
                # Extraer cada propiedad si existe en el bloque
                for line in block.splitlines():
                    if ':' in line:
                        key, val = line.split(':', 1)
                        key = key.strip()
                        val = val.strip()

                        if key == 'Wavelength (nm)':
                            row[f'{prefix}_Wavelength'] = val
                        elif key == 'Transfer Distance (m)':
                            row[f'{prefix}_Distance'] = val
                        elif key == 'Vendor Part Number':
                            row[f'{prefix}_PartNumber'] = val
                        elif key == 'Manu. Serial Number':
                            row[f'{prefix}_SerialNumber'] = val
                        elif key == 'Manufacturing Date':
                            row[f'{prefix}_MfgDate'] = val

        data.append(row)

    # Crear DataFrame y exportar a Excel
    df = pd.DataFrame(data)
    df.to_excel(output_excel, index=False)
    print(f"Proceso completado. Se procesaron {len(df)} registros y se guardaron en: {output_excel}")

if __name__ == "__main__":
    # Ajusta los nombres de archivo según tus archivos locales
    input_xml = "resultado_inventario_sfp.xml"
    output_excel = "Inventario_SFP.xlsx"
    parse_xml_to_excel(input_xml, output_excel)