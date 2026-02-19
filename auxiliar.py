import pandas as pd

def procesar_archivos(df_main, df_ingreso):
    # 1. Normalización de la columna clave 'Código'
    df_main['Código'] = df_main['Código'].astype(str).str.strip()
    df_ingreso['Código'] = df_ingreso['Código'].astype(str).str.strip()

    # --- PASO CRUCIAL: Convertir Cantidad a numérico ---
    # Esto evita el error TypeError: unsupported operand type(s) for +: 'float' and 'str'
    df_ingreso['Cantidad'] = pd.to_numeric(df_ingreso['Cantidad'], errors='coerce').fillna(0)

    # 2. Agrupar cantidades del ingreso
    # Ahora que 'Cantidad' es numérica, .sum() funcionará correctamente
    ingreso_agrupado = df_ingreso.groupby('Código')['Cantidad'].sum().reset_index()

    # 3. Fusión de datos (Left Join)
    # 
    df_merged = pd.merge(df_main, ingreso_agrupado, on='Código', how='left')

    # 4. Tratamiento de valores nulos
    df_merged['Cantidad'] = df_merged['Cantidad'].fillna(0)

    # 5. Actualización de Stocks
    cols_a_sumar = ['Stock SF', 'Stock Total']
    
    for col in cols_a_sumar:
        # Aseguramos que la columna del repo también sea numérica
        df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0.0)
        
        # Realizamos la suma
        df_merged[col] = df_merged[col] + df_merged['Cantidad']

    # 6. Limpieza final
    df_final = df_merged.drop(columns=['Cantidad'])
    
    return df_final

# Carga de archivos
try:
    df_main = pd.read_csv('bajada_repo_tactica_ACTUALIZADA.csv', low_memory=False)
    df_ingreso = pd.read_excel('OCaIngresar.xlsx')

    # Ejecución
    df_resultado = procesar_archivos(df_main, df_ingreso)

    # Guardar resultado
    df_resultado.to_csv('bajada_repo_tactica_actualizada_2301.csv', index=False)
    print("Archivo procesado y guardado con éxito como 'bajada_repo_tactica_actualizada_2301.csv'")

except FileNotFoundError as e:
    print(f"Error: No se encontró el archivo. {e}")
except Exception as e:
    print(f"Ocurrió un error: {e}")