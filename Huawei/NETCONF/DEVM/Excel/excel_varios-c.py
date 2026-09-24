import xml.etree.ElementTree as ET
import pandas as pd


def xml_a_excel(
    xml_path="resultado_inventario_sfp_devm-c.xml", excel_path="reporte_sfp.xlsx"
):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Mapeo de namespaces detectados en la respuesta
    namespaces = {
        "nc": "urn:ietf:params:xml:ns:netconf:base:1.0",
        "devm": "urn:huawei:yang:huawei-devm",
        "pic": "urn:huawei:yang:huawei-pic",
    }

    filas = []

    for router in root.findall("router"):
        nombre_router = router.get("nombre")
        host_router = router.get("host")

        # Verificar si hubo error en la conexión
        error_node = router.find("error")
        if error_node is not None:
            filas.append(
                {
                    "Nombre Router": nombre_router,
                    "Host / IP": host_router,
                    "Puerto": "N/A",
                    "Estado Admin": "N/A",
                    "SFP Vendor PN": "N/A",
                    "SFP Wavelength (nm)": "N/A",
                    "Distancia Transmision": "N/A",
                    "Fecha Fabricacion": "N/A",
                    "Número Serie SFP": "N/A",
                    "Observación / Error": error_node.text,
                }
            )
            continue

        # Buscar los puertos dentro de <nc:data>/<devm:devm>/<devm:ports>/<devm:port>
        ports = router.findall(".//devm:port", namespaces)

        if not ports:
            # Caso donde conectó pero no devolvió puertos
            filas.append(
                {
                    "Nombre Router": nombre_router,
                    "Host / IP": host_router,
                    "Puerto": "Sin datos",
                    "Estado Admin": "N/A",
                    "SFP Vendor PN": "N/A",
                    "SFP Wavelength (nm)": "N/A",
                    "Distancia Transmision": "N/A",
                    "Fecha Fabricacion": "N/A",
                    "Número Serie SFP": "N/A",
                    "Observación / Error": "Sin información de puertos",
                }
            )
            continue

        for port in ports:
            pos_elem = port.find("devm:position", namespaces)
            admin_elem = port.find("devm:admin-state", namespaces)
            opt_elem = port.find("pic:optical-module", namespaces)

            puerto = pos_elem.text if pos_elem is not None else "Desconocido"
            admin_state = (
                admin_elem.text if admin_elem is not None else "N/A"
            )

            # Datos del SFP si está presente
            if opt_elem is not None:
                vendor_pn = opt_elem.findtext(
                    "pic:vendor-pn", default="N/A", namespaces=namespaces
                )
                wavelength = opt_elem.findtext(
                    "pic:wavelength", default="N/A", namespaces=namespaces
                )
                trans_dist = opt_elem.findtext(
                    "pic:transmission-distance",
                    default="N/A",
                    namespaces=namespaces,
                )
                mfg_date = opt_elem.findtext(
                    "pic:manufacture-date",
                    default="N/A",
                    namespaces=namespaces,
                )
                sn = opt_elem.findtext(
                    "pic:serial-number", default="N/A", namespaces=namespaces
                )
                obs = "SFP Insertado"
            else:
                vendor_pn = "N/A"
                wavelength = "N/A"
                trans_dist = "N/A"
                mfg_date = "N/A"
                sn = "N/A"
                obs = "Puerto sin SFP"

            filas.append(
                {
                    "Nombre Router": nombre_router,
                    "Host / IP": host_router,
                    "Puerto": puerto,
                    "Estado Admin": admin_state,
                    "SFP Vendor PN": vendor_pn,
                    "SFP Wavelength (nm)": wavelength,
                    "Distancia Transmision": trans_dist,
                    "Fecha Fabricacion": mfg_date,
                    "Número Serie SFP": sn,
                    "Observación / Error": obs,
                }
            )

    # Crear el DataFrame y exportar a Excel
    df = pd.DataFrame(filas)
    df.to_excel(excel_path, index=False)
    print(
        f"📊 ¡Exportación completa! Se procesaron {len(filas)} filas en el archivo '{excel_path}'."
    )


if __name__ == "__main__":
    xml_a_excel()