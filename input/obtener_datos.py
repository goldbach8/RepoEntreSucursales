import requests
import pandas as pd

def _to_dataframe(root):
    """
    Emula la lógica de 'ToTable' en Power Query:
    - lista de records  -> DataFrame con columnas
    - lista de valores  -> DataFrame con una columna 'Value'
    - record (dict)     -> DataFrame de una sola fila
    """
    if isinstance(root, list):
        if not root:
            return pd.DataFrame()
        if all(isinstance(x, dict) for x in root):
            return pd.DataFrame(root)
        else:
            return pd.DataFrame({"Value": root})
    elif isinstance(root, dict):
        return pd.DataFrame([root])
    else:
        raise ValueError("Estructura de respuesta no prevista. Ajustá el parseo según el esquema real.")

def fetch_netsuite_df(
    valor,
    consulta,
    base_url="https://netsuiteapi-b0akczdxfzfea9f6.brazilsouth-01.azurewebsites.net/api/",
    endpoint="netsuite",
    timeout_minutes=120,
    headers=None,
):
    """
    Llama al endpoint y devuelve un DataFrame.
    - valor: equivalente a p_rVApCR64K26 en tu consulta M
    - consulta: 'cons_facturas' por defecto (idConsulta)
    """
    # Construcción de URL como en RelativePath
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")

    # Headers por defecto (pueden sobreescribirse)
    _headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers:
        _headers.update(headers)

    # Body equivalente a BodyRec/BodyJson
    body = {
        "rVApCR64K26": valor,
        "idConsulta": consulta,
    }

    # Timeout de 4 minutos (#duration(0,0,4,0) en Power Query)
    timeout_seconds = int(timeout_minutes * 60)

    # POST y parseo
    resp = requests.post(url, headers=_headers, json=body, timeout=timeout_seconds)
    resp.raise_for_status()  # levanta HTTPError si status != 200

    # Intentamos parsear JSON
    try:
        parsed = resp.json()
    except ValueError:
        # Si no es JSON, devolvemos texto para diagnóstico
        raise ValueError(f"La respuesta no es JSON válido. Respuesta cruda:\n{resp.text[:1000]}")

    # Emula el bloque 'Root' de tu M: si tiene 'result', lo toma; si no, usa parsed
    if isinstance(parsed, dict) and "result" in parsed:
        root = parsed["result"]
    else:
        root = parsed

    # Convertimos a DataFrame con la misma lógica que en M
    return _to_dataframe(root)

# --- Ejemplo de uso ---
# Reemplazá 12345 por el valor real que usás en p_rVApCR64K26
df = fetch_netsuite_df(valor='e/Otty(0B:2X]Oq98e%4>6p}HTU(', consulta="cons_repo_sucursales")
print(df.head())
df.to_csv('bajada_repo_sucursales.csv', index=False)