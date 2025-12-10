import pandas as pd
import numpy as np
import math

def determinar_familia_logica(row):
    """
    Define la familia lógica según reglas 1-a a 1-f.
    """
    sf = str(row.get('subfamilia', '')).upper()
    sf2 = str(row.get('subfamilia2', '')).upper()
    
    # Orden de precedencia según especificidad
    if 'GET KTN' in sf2 or 'FIJACION GET' in sf2:
        return 'GET'
    elif 'RODAJE KTN' in sf2 or 'FIJACION RODAJE' in sf2:
        return 'RODAJE'
    elif 'DONALDSON' in sf:
        return 'DONALDSON'
    elif 'TURBO' in sf:
        return 'TURBO'
    elif 'IMPORTADOS' in sf and 'FILTROS KTN' in sf2:
        return 'KTN'
    elif 'CAT ALTERNATIVO' in sf2 or 'NORDIC LIGHTS' in sf:
        return 'REPUESTOS'
    else:
        return 'OTROS'

def calcular_parametros_w(df):
    # Asignar familia lógica primero
    df['familia_logica'] = df.apply(determinar_familia_logica, axis=1)

    # Evitar división por cero
    df['qpres_total'] = df['qpres_total'].replace(0, 1) 
    df['Wp'] = df['qrem_total'] / df['qpres_total']
    
    familia_stats = df.groupby('familia_logica')[['qrem_total', 'qpres_total']].sum().reset_index()
    # Evitar división por cero en familias
    familia_stats['qpres_total'] = familia_stats['qpres_total'].replace(0, 1)
    familia_stats['Wf'] = familia_stats['qrem_total'] / familia_stats['qpres_total']
    
    df = df.merge(familia_stats[['familia_logica', 'Wf']], on='familia_logica', how='left')
    df['Wf'] = df['Wf'].fillna(0)
    return df

def estimar_demanda(df, metodo):
    """
    Estima demanda para cada SUCURSAL individualmente y luego SUMA para el TOTAL.
    Esto asegura coherencia "física".
    """
    sucursales = {
        'sf': ('qremsf', 'qpressf'),
        'ba': ('qremba', 'qpresba'),
        'mdz': ('qremmdz', 'qpresmdz'),
        'slt': ('qremslt', 'qpresslt')
    }

    def calcular_demanda_fila(row, col_rem, col_pres):
        if col_rem not in row or col_pres not in row:
            return 0
            
        rem = row[col_rem]
        pres = row[col_pres]
        
        # Metodo A
        if metodo == 'A':
            Wp = row['Wp']
            Wf = row['Wf']
            if Wp < Wf:
                return Wf * pres 
            else:
                return 1.1 * rem
        
        # Metodo B
        else:
            if rem == 0:
                return pres * 0.5
            elif pres > rem and pres < (rem * 1.5):
                return (pres + rem) / 2
            elif pres >= (rem * 1.5):
                return rem * 1.5
            else:
                return rem

    # 1. Calcular demanda individual para cada sucursal
    cols_demanda_suc = []
    for suc, (c_rem, c_pres) in sucursales.items():
        col_name = f'demanda_estimada_{suc}'
        cols_demanda_suc.append(col_name)
        
        if c_rem not in df.columns: df[c_rem] = 0
        if c_pres not in df.columns: df[c_pres] = 0
        
        df[col_name] = df.apply(lambda x: calcular_demanda_fila(x, c_rem, c_pres), axis=1)

    # 2. Calcular la Demanda Total como la suma de las demandas de sucursales
    df['demanda_estimada_total'] = df[cols_demanda_suc].sum(axis=1)

    return df

def calcular_coberturas(df, cob_sf, cob_ba, cob_mdz, cob_slt):
    """
    Calcula coberturas y diferencias (Sobra/Falta).
    Las columnas 'diff_{suc}' y 'diff_sf' contienen la diferencia EXACTA (real).
    """
    # 1. Cobertura TOTAL (GLOBAL)
    if 'stock_total' not in df.columns: df['stock_total'] = 0
    df['cobertura_ini_total'] = df['stock_total'] / df['demanda_estimada_total'].replace(0, 0.00001)

    # 2. Santa Fe
    cols_sf_fisico = ['stock_sf', 'stock_aux', 'stock_sv_arg', 'stock_sv_min', 'stock_ns_noa']
    for c in cols_sf_fisico:
        if c not in df.columns: df[c] = 0
        
    df['stock_total_sf_fisico'] = df[cols_sf_fisico].sum(axis=1)
    stock_sf_calculo = df['stock_total_sf_fisico'] + df.get('qty_ee_transito_sf', 0)
    
    df['cobertura_ini_sf'] = stock_sf_calculo / df['demanda_estimada_sf'].replace(0, 0.00001)
    
    # --- LOGICA DE BALANCEO SF ---
    # Objetivo real = MIN(Objetivo Usuario, Cobertura Global)
    df['target_sf_eff'] = np.minimum(cob_sf, df['cobertura_ini_total'])
    stock_obj_sf = df['demanda_estimada_sf'] * df['target_sf_eff']
    
    # Diferencia Real SF (Sin redondear)
    df['diff_sf'] = stock_sf_calculo - stock_obj_sf

    # 3. Sucursales (Individuales)
    config_sucursales = {
        'ba': cob_ba,
        'mdz': cob_mdz,
        'slt': cob_slt
    }
    
    for suc, cob_target_usuario in config_sucursales.items():
        col_stock = f'stock_{suc}'
        col_transito = f'qty_transito_{suc}'
        if suc == 'slt': col_transito = 'qty_ot_transito_slt'
        
        stk = df[col_stock] if col_stock in df.columns else 0
        trs = df[col_transito] if col_transito in df.columns else 0
        
        stock_suc_total = stk + trs
        col_demanda_local = f'demanda_estimada_{suc}'
        
        df[f'cobertura_ini_{suc}'] = stock_suc_total / df[col_demanda_local].replace(0, 0.00001)
        
        # Balanceo por Escasez
        target_suc_eff = np.minimum(cob_target_usuario, df['cobertura_ini_total'])
        stock_obj_ideal = df[col_demanda_local] * target_suc_eff
        
        # Diferencia Real Sucursal (Sin redondear)
        df[f'diff_{suc}'] = stock_suc_total - stock_obj_ideal

    return df

def distribuir_stock(df):
    """
    Define los envíos. AQUÍ transformamos la "Falta Real" y "Sobra Real" en "Cantidad de Cajas a Enviar".
    """
    sucursales = ['ba', 'mdz', 'slt']
    
    def calcular_fila(row):
        lote = row['qty_piezas']
        if pd.isna(lote) or lote <= 0: lote = 1
        
        # 1. Determinar Disponibilidad de Envío desde SF (Lógica Supply)
        diff_sf_real = row['diff_sf']
        
        if diff_sf_real > 0:
            # Disponibilidad: Usamos el entero hacia abajo, pero permitiendo el uso de stock
            disponible_sf = math.floor(diff_sf_real)
        else:
            disponible_sf = 0
        
        # --- PROTECCIÓN DE INTEGRIDAD SF (No romper el último juego físico) ---
        stock_fisico_sf = row['stock_total_sf_fisico']
        
        if lote > 1 and stock_fisico_sf >= lote:
            # Lo máximo que puede dar es (StockFisico - 1 Caja) para no quedarse con una caja rota inutilizable si es política
            maximo_dable_seguridad = max(0, stock_fisico_sf - lote)
            disponible_sf = min(disponible_sf, maximo_dable_seguridad)
        # -----------------------------------------------
        
        envios_deseados = {}
        total_deseado = 0
        
        # 2. Calcular NECESIDADES de envío (Lógica Demand)
        for suc in sucursales:
            diferencia_real = row.get(f'diff_{suc}', 0)
            
            if diferencia_real < 0:
                falta_real = abs(diferencia_real)
                
                # APLICAMOS LÓGICA FLEXIBLE PARA TODOS (Sin distinción de familia)
                # Esto soluciona el problema de que Donaldson/Turbo redondeen a 0 cuando falta casi 1 caja.
                qty_a_pedir = calcular_qty_a_pedir(falta_real, lote)
                
                envios_deseados[suc] = qty_a_pedir
                total_deseado += qty_a_pedir
            else:
                envios_deseados[suc] = 0
        
        # 3. Distribuir lo disponible proporcionalmente
        envios_finales = {suc: 0 for suc in sucursales}
        
        if disponible_sf <= 0:
            return pd.Series(envios_finales)
            
        if disponible_sf >= total_deseado:
            # Hay suficiente para cubrir todos los deseos calculados
            for suc, qty in envios_deseados.items():
                envios_finales[suc] = qty
            return pd.Series(envios_finales)
            
        if total_deseado > 0:
            # Escasez: Prorratear
            ratio = disponible_sf / total_deseado
            acumulado = 0
            for suc, qty_deseada in envios_deseados.items():
                if qty_deseada > 0:
                    cantidad_proporcional = qty_deseada * ratio
                    # Al prorratear en escasez, priorizamos enviar unidades enteras
                    cantidad_reale = math.floor(cantidad_proporcional)
                    
                    if (acumulado + cantidad_reale) <= disponible_sf:
                        envios_finales[suc] = cantidad_reale
                        acumulado += cantidad_reale
                    else:
                        remanente = disponible_sf - acumulado
                        envios_finales[suc] = remanente
                        acumulado += remanente
        
        return pd.Series(envios_finales)

    cols_envios = df.apply(calcular_fila, axis=1)
    
    for suc in sucursales:
        df[f'final_enviar_{suc}'] = cols_envios[suc]

    return df

def calcular_qty_a_pedir(necesidad, lote):
    """
    Lógica de redondeo flexible unificada.
    Objetivo: Acercarse a cajas cerradas si es posible, pero permitir romper caja
    si la necesidad es muy específica o si el redondeo perjudica el abastecimiento.
    """
    if pd.isna(lote) or lote <= 1: return necesidad
    
    # 1. Calcular cajas teóricas (Redondeo matemático estándar: 1.6 -> 2, 1.4 -> 1)
    cajas_teoricas = necesidad / lote
    cajas_redondeadas = round(cajas_teoricas)
    qty_redondeada = cajas_redondeadas * lote
    
    # 2. Verificar cuánto nos desviamos de la necesidad real
    diferencia = abs(necesidad - qty_redondeada)
    
    # Umbral de tolerancia: 30% del tamaño de la caja
    # Si la diferencia es menor al 30%, aceptamos la caja cerrada.
    umbral = lote * 0.30
    
    if diferencia <= umbral:
        # Caso especial: El redondeo da 0 (ej: necesidad 4, lote 12 -> round(0.33)=0)
        # Si la necesidad es "relevante" (> 25% de la caja), NO mandamos 0, mandamos exacto.
        if qty_redondeada == 0 and necesidad >= (lote * 0.25):
            return necesidad # Rompemos caja y mandamos 4 unidades
        
        return qty_redondeada # Mandamos cajas cerradas (ej: need 11, lote 12 -> 12)
    else:
        # Si la diferencia es muy grande (ej: need 18, lote 12 -> round=24, diff=6, umbral=3.6)
        # Significa que estamos "en el medio". Mandamos la cantidad exacta.
        return necesidad

def calcular_excedentes_sucursales(df, umbral_meses_exceso=0.5):
    """
    Identifica excedentes en sucursales.
    """
    sucursales = ['ba', 'mdz', 'slt']
    
    for c in ['peso', 'volumen']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    obj_sf = 0.5 
    stock_sf_total = df['stock_total_sf_fisico'] + df.get('qty_ee_transito_sf', 0)
    target_sf = df['demanda_estimada_sf'] * obj_sf
    df['sf_deficit'] = target_sf - stock_sf_total
    df['sf_necesita_stock'] = df['sf_deficit'] > 0

    for suc in sucursales:
        col_stock = f'stock_{suc}'
        col_demanda = f'demanda_estimada_{suc}'
        col_transito = f'qty_transito_{suc}'
        if suc == 'slt': col_transito = 'qty_ot_transito_slt'

        stock_suc = df[col_stock] + df.get(col_transito, 0)
        demanda_suc = df[col_demanda]
        
        cobertura_actual = stock_suc / demanda_suc
        
        mask_exceso = (cobertura_actual > umbral_meses_exceso) & (df[col_stock] > 0)
        
        stock_ideal_max = demanda_suc * umbral_meses_exceso
        excedente_teorico = stock_suc - stock_ideal_max
        excedente_real = np.minimum(excedente_teorico, df[col_stock])
        excedente_final = np.floor(excedente_real)
        
        col_excedente = f'excedente_qty_{suc}'
        df[col_excedente] = 0
        df.loc[mask_exceso, col_excedente] = excedente_final
        df[col_excedente] = df[col_excedente].clip(lower=0)
        
        df[f'excedente_peso_{suc}'] = df[col_excedente] * df['peso']
        df[f'excedente_vol_{suc}'] = df[col_excedente] * df['volumen']
        
        df[f'prioridad_retorno_{suc}'] = (df[col_excedente] > 0) & (df['sf_necesita_stock'])

    return df