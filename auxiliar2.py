import pandas as pd

# 1. Nombres de los archivos (asegúrate de que coincidan exactamente)
archivo_csv_repo = 'bajada_repo_tactica_coregido_3012.csv'
archivo_excel_stock = 'Stock actual en sucursales Turbo - DNS - Filtros KTN (1).xlsx'

print("Cargando archivos...")

try:
    # 2. Cargar los datos
    # Usamos low_memory=False por si el CSV es muy grande
    df_repo = pd.read_csv(archivo_csv_repo, low_memory=False)
    df_stock = pd.read_excel(archivo_excel_stock)

    # 3. Preparar las claves de cruce (limpiar espacios y normalizar a mayúsculas)
    df_repo['key'] = df_repo['Código'].astype(str).str.strip().str.upper()
    df_stock['key'] = df_stock['codigo'].astype(str).str.strip().str.upper()

    # 4. Definir el mapeo: { Columna_en_Excel : Columna_en_CSV }
    mapping = {
        'stock_actual': 'Stock Total',
        'stock_sf': 'Stock SF',
        'stock_ba': 'Stock BA',
        'stock_mdz': 'Stock MDZ',
        'stock_sa': 'Stock SLT',
        'stock_sv_arg': 'Stock SV ARG',
        'stock_sv_min': 'Stock SV MIN'
    }

    # 5. Realizar el cruce de datos
    # Traemos solo las columnas necesarias del Excel al DataFrame del Repo
    cols_excel = ['key'] + list(mapping.keys())
    df_merged = pd.merge(df_repo, df_stock[cols_excel], on='key', how='left')

    # 6. Actualizar valores
    # Identificamos qué filas del repo existen en el archivo de stock
    encontrados = df_merged['key'].isin(df_stock['key'])

    for col_excel, col_repo in mapping.items():
        # Para los códigos encontrados, reemplazamos el valor del repo por el del excel
        # Si el valor en el excel es nulo, ponemos 0
        df_merged.loc[encontrados, col_repo] = df_merged.loc[encontrados, col_excel].fillna(0)

    # 7. Limpieza final: eliminar columnas auxiliares creadas para el proceso
    columnas_a_borrar = ['key'] + list(mapping.keys())
    df_final = df_merged.drop(columns=columnas_a_borrar)

    # 8. Guardar el resultado
    nombre_salida = 'bajada_repo_tactica_ACTUALIZADA.csv'
    df_final.to_csv(nombre_salida, index=False)

    print(f"¡Éxito! Se actualizaron {encontrados.sum()} registros.")
    print(f"Archivo guardado como: {nombre_salida}")

except FileNotFoundError as e:
    print(f"Error: No se encontró uno de los archivos. Verifica los nombres. \nDetalle: {e}")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")