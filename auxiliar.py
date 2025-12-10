import pandas as pd
import io

# Simulamos la carga de archivos (en tu caso, estos archivos ya existen en tu carpeta)
df_main = pd.read_csv('bajada_repo_tactica.csv')
df_ingreso = pd.read_excel('OCaIngresar.xlsx')

def procesar_archivos(df_main, df_ingreso):
    # 1. Normalización de la columna clave 'Código'
    # Convertimos a string y eliminamos espacios en blanco para asegurar coincidencias
    df_main['Código'] = df_main['Código'].astype(str).str.strip()
    df_ingreso['Código'] = df_ingreso['Código'].astype(str).str.strip()

    # 2. Agrupar cantidades del ingreso
    # Es posible que un mismo código aparezca varias veces en el ingreso, así que sumamos sus cantidades
    ingreso_agrupado = df_ingreso.groupby('Código')['Cantidad'].sum().reset_index()

    # 3. Fusión de datos (Left Join)
    # Unimos la tabla principal con las cantidades agrupadas. 
    # 'left' asegura que mantenemos todas las filas del inventario original.
    df_merged = pd.merge(df_main, ingreso_agrupado, on='Código', how='left')

    # 4. Tratamiento de valores nulos en la nueva columna 'Cantidad'
    # Si no hubo coincidencia (el producto no estaba en el ingreso), la cantidad a sumar es 0
    df_merged['Cantidad'] = df_merged['Cantidad'].fillna(0)

    # 5. Actualización de Stocks
    cols_a_sumar = ['Stock SF', 'Stock Total']
    
    for col in cols_a_sumar:
        # Forzamos que la columna sea numérica, convirtiendo errores (texto) a NaN y luego a 0.0
        df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0.0)
        
        # Sumamos la cantidad del ingreso al stock existente
        df_merged[col] = df_merged[col] + df_merged['Cantidad']

    # 6. Limpieza final
    # Eliminamos la columna auxiliar 'Cantidad' que usamos para la suma
    df_final = df_merged.drop(columns=['Cantidad'])
    
    return df_final

# Ejecución del procesamiento
df_resultado = procesar_archivos(df_main, df_ingreso)

# Guardar resultado
df_resultado.to_csv('bajada_repo_tactica_coregido.csv', index=False)
#print("Archivo guardado con éxito.")