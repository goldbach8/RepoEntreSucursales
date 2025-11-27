import pandas as pd
import os

# --- CONFIGURACIÓN ---
NOMBRE_ARCHIVO_ENTRADA = 'Cantidad Remitida y Presupuestada por Sucursal 21-11-25.xlsx'
NOMBRE_ARCHIVO_SALIDA = 'INPUT_STANDARD_APP_corregido.csv'

def procesar_archivo():
    if not os.path.exists(NOMBRE_ARCHIVO_ENTRADA):
        print(f"❌ Error: No se encuentra el archivo '{NOMBRE_ARCHIVO_ENTRADA}'")
        return

    print(f"🔄 Procesando '{NOMBRE_ARCHIVO_ENTRADA}'...")

    try:
        # 1. Lectura inteligente (detecta ; o , y encoding)
        # Intentamos primero con punto y coma (común en tu archivo)
        try:
            df = pd.read_excel(NOMBRE_ARCHIVO_ENTRADA, sheet_name="Hoja1")
        except:
            try:
                df = pd.read_csv(NOMBRE_ARCHIVO_ENTRADA, sep=';', encoding='utf-8', on_bad_lines='skip')
            except:
                df = pd.read_csv(NOMBRE_ARCHIVO_ENTRADA, sep=',', encoding='latin-1', on_bad_lines='skip')

        # Normalizar nombres actuales a minusculas y sin espacios para facilitar el mapeo
        df.columns = df.columns.str.strip().str.lower()
        
        print(f"   -> Columnas encontradas: {list(df.columns[:5])} ...")

        # 2. Diccionario de Mapeo (Tu archivo -> Estándar App)
        rename_map = {
            'código': 'codigo',
            'descripción': 'descripcion',
            'subfamilia': 'subfamilia',
            'subfamilia2': 'subfamilia2',
            'inhabilitado': 'inhabilitado',
            'peso': 'peso',
            'qty piezas': 'qty_piezas',
            
            # Totales
            'qpres total': 'qpres_total',
            'qrem total': 'qrem_total',
            'stock total': 'stock_total',
            
            # Santa Fe
            'qpressf': 'qpressf',
            'qremsf': 'qremsf',
            'stock sf': 'stock_sf',
            'stock aux': 'stock_aux',
            'stock sv arg': 'stock_sv_arg',
            'stock sv min': 'stock_sv_min',
            'stock ns noa': 'stock_ns_noa',
            'stock sf final': 'stock_sf_final',
            
            # Sucursales
            'qpresba': 'qpresba',
            'qremba': 'qremba',
            'stock ba': 'stock_ba',
            
            'qpresmdz': 'qpresmdz',
            'qremmdz': 'qremmdz',
            'stock mdz': 'stock_mdz',
            
            'qpresslt': 'qpresslt',
            'qremslt': 'qremslt',
            'stock slt': 'stock_slt',
            
            # Extras
            'familia': 'familia'
        }

        # Renombrar
        df = df.rename(columns=rename_map)
        
        # 3. Rellenar columnas faltantes con 0 (Para evitar NaN en la app)
        columnas_necesarias_extra = [
            'qty_ee_transito_sf',
            'qty_ot_transito_sf',
            'qty_transito_ba',
            'qty_transito_mdz',
            'qty_ot_transito_slt'
        ]
        
        for col in columnas_necesarias_extra:
            if col not in df.columns:
                print(f"   -> Agregando columna faltante (en 0): {col}")
                df[col] = 0

        # 4. Seleccionar solo columnas válidas para limpiar el archivo
        cols_finales = [c for c in df.columns if c in rename_map.values() or c in columnas_necesarias_extra]
        df_final = df[cols_finales]
        
        # Reemplazar NaN numéricos con 0 y textos con ""
        # Esto asegura que la app no falle por datos vacíos
        num_cols = df_final.select_dtypes(include=['float64', 'int64']).columns
        df_final[num_cols] = df_final[num_cols].fillna(0)

        # 5. Guardar
        df_final.to_csv(NOMBRE_ARCHIVO_SALIDA, index=False, sep=',', encoding='utf-8')
        
        print(f"✅ ¡Éxito! Archivo guardado como: {NOMBRE_ARCHIVO_SALIDA}")
        print("   -> Ahora puedes subir este archivo a la aplicación.")

    except Exception as e:
        print(f"❌ Error crítico procesando el archivo: {e}")

if __name__ == "__main__":
    procesar_archivo()