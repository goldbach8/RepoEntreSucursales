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

    # 2. Calcular la Demanda Total
    df['demanda_estimada_total'] = df[cols_demanda_suc].sum(axis=1)

    return df

def calcular_coberturas(df, cob_sf, cob_ba, cob_mdz, cob_slt):
    """
    Calcula coberturas y diferencias (Sobra/Falta).
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
    
    # Objetivo real
    df['target_sf_eff'] = np.minimum(cob_sf, df['cobertura_ini_total'])
    stock_obj_sf = df['demanda_estimada_sf'] * df['target_sf_eff']
    
    # Diferencia Real SF (Float)
    df['diff_sf'] = stock_sf_calculo - stock_obj_sf

    # 3. Sucursales (Individuales)
    config_sucursales = {'ba': cob_ba, 'mdz': cob_mdz, 'slt': cob_slt}
    
    for suc, cob_target_usuario in config_sucursales.items():
        col_stock = f'stock_{suc}'
        col_transito = f'qty_transito_{suc}'
        if suc == 'slt': col_transito = 'qty_ot_transito_slt'
        
        stk = df[col_stock] if col_stock in df.columns else 0
        trs = df[col_transito] if col_transito in df.columns else 0
        
        stock_suc_total = stk + trs
        col_demanda_local = f'demanda_estimada_{suc}'
        
        df[f'cobertura_ini_{suc}'] = stock_suc_total / df[col_demanda_local].replace(0, 0.00001)
        
        target_suc_eff = np.minimum(cob_target_usuario, df['cobertura_ini_total'])
        stock_obj_ideal = df[col_demanda_local] * target_suc_eff
        
        # Diferencia Real Sucursal (Float)
        df[f'diff_{suc}'] = stock_suc_total - stock_obj_ideal

    return df

def distribuir_stock(df):
    """
    Define los envíos aplicando lógica de cajas (Filtros) y juegos (No Filtros).
    """
    sucursales = ['ba', 'mdz', 'slt']
    # Familias consideradas "Filtros" para lógica de cajas
    familias_filtros = ['DONALDSON', 'TURBO', 'KTN'] 
    
    def calcular_fila(row):
        qty_p = row['qty_piezas']
        if pd.isna(qty_p) or qty_p <= 0: qty_p = 1
        
        fam = row['familia_logica']
        es_filtro = fam in familias_filtros
        
        # --- 1. DISPONIBILIDAD SANTA FE (PISO DEL SOBRANTE) ---
        diff_sf_real = row['diff_sf']
        stock_fisico_sf = row['stock_total_sf_fisico']
        
        if diff_sf_real > 0:
            if es_filtro:
                # Lógica Filtros: Disponibilidad simple (floor)
                disponible_sf = math.floor(diff_sf_real)
            else:
                # Lógica Kits (No Filtros):
                # SF debe quedarse con stock suficiente para cubrir su demanda target 
                # PERO en múltiplos de juegos completos (qty_piezas).
                # Calculamos cuánto necesita SF redondeado hacia arriba al próximo kit.
                demanda_sf = row['demanda_estimada_sf']
                target_sf_cob = row['target_sf_eff'] # Cobertura efectiva usada
                stock_target_sf = demanda_sf * target_sf_cob
                
                # Cuántos kits completos necesita retener SF para estar cubierto
                kits_necesarios_sf = math.ceil(stock_target_sf / qty_p)
                stock_retencion_sf = kits_necesarios_sf * qty_p
                
                # Lo que sobra por encima de la retención de kits
                # Usamos el stock calculado (fisico+transito) que es el que se usó para diff_sf
                stock_calculo_sf = row['diff_sf'] + stock_target_sf # Reconstrucción inversa o usar cols directas
                # Mejor usar directamente la resta lógica:
                # Disponible = Stock_Total_SF - Retencion_Kits
                # (Asumiendo que diff_sf se calculó sobre stock_calculo_sf)
                stock_total_sf = row['stock_total_sf_fisico'] + row.get('qty_ee_transito_sf', 0)
                
                disponible_teorico = stock_total_sf - stock_retencion_sf
                disponible_sf = max(0, int(disponible_teorico))
                
        else:
            disponible_sf = 0
        
        # Seguridad: Nunca enviar más de lo que hay físicamente
        disponible_sf = min(disponible_sf, stock_fisico_sf)
        
        envios_deseados = {}
        total_deseado = 0
        
        # --- 2. NECESIDAD SUCURSALES (TECHO DEL FALTANTE) ---
        for suc in sucursales:
            diferencia_real = row.get(f'diff_{suc}', 0)
            
            if diferencia_real < 0:
                # Necesidad base: Techo del faltante (Ceil)
                falta_base = math.ceil(abs(diferencia_real))
                
                qty_a_pedir = 0
                
                if es_filtro:
                    # --- LÓGICA FILTROS (Cajas) ---
                    # Ajustar a caja completa SOLO si falta poco
                    qty_a_pedir = calcular_qty_filtros(falta_base, qty_p)
                else:
                    # --- LÓGICA KITS (Juegos) ---
                    # Completar juego en destino
                    col_stock = f'stock_{suc}'
                    col_trans = f'qty_transito_{suc}' if suc != 'slt' else 'qty_ot_transito_slt'
                    stock_suc_actual = row.get(col_stock, 0) + row.get(col_trans, 0)
                    
                    qty_a_pedir = calcular_qty_kits(falta_base, stock_suc_actual, qty_p)
                
                envios_deseados[suc] = qty_a_pedir
                total_deseado += qty_a_pedir
            else:
                envios_deseados[suc] = 0
        
        # --- 3. DISTRIBUCIÓN ---
        envios_finales = {suc: 0 for suc in sucursales}
        
        if disponible_sf <= 0:
            return pd.Series(envios_finales)
            
        if disponible_sf >= total_deseado:
            for suc, qty in envios_deseados.items():
                envios_finales[suc] = qty
            return pd.Series(envios_finales)
            
        # Escasez: Prorratear (Waterfall simple o proporcional entero)
        if total_deseado > 0:
            ratio = disponible_sf / total_deseado
            acumulado = 0
            for suc, qty_deseada in envios_deseados.items():
                if qty_deseada > 0:
                    cant_prop = math.floor(qty_deseada * ratio)
                    if (acumulado + cant_prop) <= disponible_sf:
                        envios_finales[suc] = cant_prop
                        acumulado += cant_prop
                    else:
                        rem = disponible_sf - acumulado
                        envios_finales[suc] = rem
                        acumulado += rem
        
        return pd.Series(envios_finales)

    cols_envios = df.apply(calcular_fila, axis=1)
    for suc in sucursales:
        df[f'final_enviar_{suc}'] = cols_envios[suc]

    return df

def calcular_qty_filtros(necesidad, lote):
    """
    Regla Filtros:
    - Caja 6: Completar si tengo 4 o 5 (falta 1 o 2 para llegar a 6).
    - Caja 12: Completar si tengo 9, 10, 11 (falta 1, 2 o 3 para llegar a 12).
    """
    if lote <= 1: return necesidad
    
    # Cuántas unidades sueltas tengo en esa necesidad teórica
    # (Ej: Necesito 16, Lote 6 -> 2 cajas (12) + 4 sueltas)
    resto = necesidad % lote
    
    if resto == 0:
        return necesidad # Ya es múltiplo
        
    adicional_para_cerrar = lote - resto
    
    if lote == 6:
        # Si tengo 4 o 5 (faltan 2 o 1), cierro caja
        if adicional_para_cerrar <= 2:
            return necesidad + adicional_para_cerrar
    elif lote == 12:
        # Si tengo 9, 10, 11 (faltan 3, 2 o 1), cierro caja
        if adicional_para_cerrar <= 3:
            return necesidad + adicional_para_cerrar
            
    # Si no cumple condición de cierre, mando necesidad exacta (rompiendo caja en origen)
    return necesidad

def calcular_qty_kits(necesidad_base, stock_actual, lote):
    """
    Regla Kits (No Filtros):
    (Stock_Actual + Envio) debe ser múltiplo de Lote (Juego).
    """
    if lote <= 1: return necesidad_base
    
    objetivo_minimo = stock_actual + necesidad_base
    
    # Buscar el siguiente múltiplo de lote que cubra el objetivo
    # ceil(15 / 6) * 6 = 3 * 6 = 18
    kits_necesarios = math.ceil(objetivo_minimo / lote)
    stock_final_deseado = kits_necesarios * lote
    
    envio_calculado = stock_final_deseado - stock_actual
    
    # Corrección: Si el stock actual ya cubre la necesidad (raro si entramos aquí), no pedir negativo
    return max(0, int(envio_calculado))

def calcular_excedentes_sucursales(df, umbral_meses_exceso=0.5):
    """ Identifica excedentes en sucursales. """
    sucursales = ['ba', 'mdz', 'slt']
    for c in ['peso', 'volumen']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Contexto SF
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