import pandas as pd
import io

def cargar_datos(uploaded_file):
    """
    Carga el archivo CSV estándar.
    Se asume que el archivo ya ha sido pre-procesado o es el original con separadores ; o ,
    """
    if uploaded_file is not None:
        try:
            # Detección automática de separador
            content = uploaded_file.getvalue()
            try:
                sample = content[:1024].decode('utf-8')
            except:
                sample = content[:1024].decode('latin-1')
            
            sep = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
            
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, sep=sep, encoding='utf-8', on_bad_lines='skip')
            except:
                df = pd.read_csv(uploaded_file, sep=sep, encoding='latin-1', on_bad_lines='skip')

            # Normalización básica
            df.columns = df.columns.str.strip().str.lower()
            
            # Mapeo ampliado para incluir columnas visuales
            rename_map = {
                'código': 'codigo',
                'descripción': 'descripcion',
                'descripción2': 'descripcion2', 
                'descripcion2': 'descripcion2',
                'familia': 'familia',
                'subfamilia': 'subfamilia',
                'subfamilia2': 'subfamilia2', 
                'grupo stock': 'grupo_stock', 
                'grupo stock': 'grupo_stock',
                'inhabilitado': 'inhabilitado',
                'peso': 'peso',
                'volumen': 'volumen', # Nueva columna para resumen
                'qty piezas': 'qty_piezas',
                
                # Totales
                'qpres total': 'qpres_total',
                'qrem total': 'qrem_total',
                'stock total': 'stock_total',
                
                # Santa Fe
                'qpressf': 'qpressf',
                'qremsf': 'qremsf',
                'stock sf': 'stock_sf',
                'stock sf final': 'stock_sf_final',
                'stock aux': 'stock_aux',
                'stock sv arg': 'stock_sv_arg',
                'stock sv min': 'stock_sv_min',
                'stock ns noa': 'stock_ns_noa',
                
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

                # Extras y Aplicaciones
                'datos_y_aplicaciones': 'datos_y_aplicaciones'
            }
            
            df = df.rename(columns=rename_map)
            
            # Relleno de columnas necesarias para lógica
            cols_relleno = [
                'qty_ee_transito_sf', 'qty_ot_transito_sf',
                'qty_transito_ba', 'qty_transito_mdz', 'qty_ot_transito_slt',
                'qpres_total', 'qrem_total', # Por seguridad
                'peso', 'volumen'
            ]
            for col in cols_relleno:
                if col not in df.columns:
                    df[col] = 0

            return df
        except Exception as e:
            return None
    return None

def generar_csv_ejemplo():
    """ Genera CSV ejemplo (Simplificado) """
    data = {'codigo': ['A1'], 'descripcion': ['Ejemplo']}
    return pd.DataFrame(data).to_csv(index=False).encode('utf-8')

def validar_columnas(df):
    """ Valida columnas críticas para el CÁLCULO """
    columnas_requeridas = [
        'codigo', 'subfamilia', 'qpres_total', 'qrem_total', 
        'qty_piezas', 'peso', 'stock_sf', 'stock_ba', 'stock_mdz', 'stock_slt'
    ]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    return faltantes

def aplicar_filtros_avanzados(df, ignorar_inhabilitados, ignorar_sin_stock, ignorar_sin_demanda, ignorar_dns):
    df_filtrado = df.copy()
    
    # Normalizar columnas para evitar errores de mayusculas/espacios
    if 'grupo_stock' in df_filtrado.columns:
        df_filtrado['grupo_stock_norm'] = df_filtrado['grupo_stock'].astype(str).str.strip().str.upper()

    if ignorar_inhabilitados and 'inhabilitado' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['inhabilitado'].astype(str).str.lower() != 'si']

    # --- CAMBIO 3: Filtro DNS ---
    if ignorar_dns and 'grupo_stock_norm' in df_filtrado.columns:
        valores_dns = ['DNS - A DEMANDA', 'DNS - INMOVILIZADO', 'TURBO - INMOVILIZADO', 'FILTROS KTN - INMOVILIZADO', 'TURBO - A DEMANDA']
        # Excluimos si contiene esos textos
        df_filtrado = df_filtrado[~df_filtrado['grupo_stock_norm'].isin(valores_dns)]

    if ignorar_sin_stock:
        if 'stock_total' in df_filtrado.columns:
             df_filtrado = df_filtrado[df_filtrado['stock_total'] > 0]
        else:
            cols_stock = [c for c in df_filtrado.columns if 'stock' in c]
            if cols_stock:
                df_filtrado = df_filtrado[df_filtrado[cols_stock].sum(axis=1) > 0]

    if ignorar_sin_demanda:
        has_qrem = 'qrem_total' in df_filtrado.columns
        has_qpres = 'qpres_total' in df_filtrado.columns
        if has_qrem and has_qpres:
            df_filtrado = df_filtrado[ (df_filtrado['qrem_total'] > 0) | (df_filtrado['qpres_total'] > 0) ]
        elif has_qrem:
             df_filtrado = df_filtrado[df_filtrado['qrem_total'] > 0]
    
    # Limpiamos columna auxiliar
    if 'grupo_stock_norm' in df_filtrado.columns:
        df_filtrado = df_filtrado.drop(columns=['grupo_stock_norm'])
        
    return df_filtrado