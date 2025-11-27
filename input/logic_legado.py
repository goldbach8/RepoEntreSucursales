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
    Estima demanda para TOTAL y para cada SUCURSAL individualmente.
    """
    suffijos = {
        'total': ('qrem_total', 'qpres_total'),
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

    for ambito, (c_rem, c_pres) in suffijos.items():
        col_name = f'demanda_estimada_{ambito}'
        if c_rem not in df.columns: df[c_rem] = 0
        if c_pres not in df.columns: df[c_pres] = 0
        
        df[col_name] = df.apply(lambda x: calcular_demanda_fila(x, c_rem, c_pres), axis=1)
        # CORRECCION: Se eliminó el reemplazo forzado de 0 a 0.001 para no ensuciar datos.
        # df[col_name] = df[col_name].replace(0, 0.001)

    return df

def calcular_coberturas(df, cob_sf, cob_ba, cob_mdz, cob_slt):
    """
    Calcula coberturas usando las demandas LOCALES y objetivos individuales.
    """
    # 1. Cobertura TOTAL
    if 'stock_total' not in df.columns: df['stock_total'] = 0
    # Manejo de division por cero implicito (pandas genera inf, lo cual es matematicamente correcto para cobertura)
    df['cobertura_ini_total'] = df['stock_total'] / df['demanda_estimada_total']

    # 2. Santa Fe (Lógica Central)
    cols_sf_fisico = ['stock_sf', 'stock_aux', 'stock_sv_arg', 'stock_sv_min', 'stock_ns_noa']
    for c in cols_sf_fisico:
        if c not in df.columns: df[c] = 0
        
    df['stock_total_sf_fisico'] = df[cols_sf_fisico].sum(axis=1)
    stock_sf_calculo = df['stock_total_sf_fisico'] + df.get('qty_ee_transito_sf', 0)
    
    # CORRECCION: Se usa demanda LOCAL para SF (stock_sf / demanda_sf)
    df['cobertura_ini_sf'] = stock_sf_calculo / df['demanda_estimada_sf']
    
    stock_obj_sf = df['demanda_estimada_sf'] * cob_sf
    df['diff_sf_raw'] = stock_sf_calculo - stock_obj_sf
    
    # Para SF usamos un ajuste simple (floor) para ser conservadores en lo que consideramos "disponible para enviar"
    df['diff_sf'] = df.apply(lambda x: ajustar_lote_simple(x['diff_sf_raw'], x['qty_piezas']), axis=1)

    # 3. Sucursales (Individuales)
    config_sucursales = {
        'ba': cob_ba,
        'mdz': cob_mdz,
        'slt': cob_slt
    }
    
    for suc, cob_target in config_sucursales.items():
        col_stock = f'stock_{suc}'
        col_transito = f'qty_transito_{suc}'
        if suc == 'slt': col_transito = 'qty_ot_transito_slt'
        
        stk = df[col_stock] if col_stock in df.columns else 0
        trs = df[col_transito] if col_transito in df.columns else 0
        
        stock_suc_total = stk + trs
        col_demanda_local = f'demanda_estimada_{suc}'
        
        # Cobertura Actual (Meses)
        df[f'cobertura_ini_{suc}'] = stock_suc_total / df[col_demanda_local]
        
        stock_obj_ideal = df[col_demanda_local] * cob_target
        
        df[f'diff_{suc}'] = df.apply(
            lambda row: calcular_diferencia_sucursal(
                row, 
                stock_suc_total_row=stock_suc_total[row.name], 
                stock_obj_ideal_row=stock_obj_ideal[row.name]
            ), 
            axis=1
        )

    return df

def calcular_diferencia_sucursal(row, stock_suc_total_row, stock_obj_ideal_row):
    fam = row['familia_logica']
    lote = row['qty_piezas']
    if pd.isna(lote) or lote <= 0: lote = 1
    
    # Diferencia Real (Lo que falta para llegar al objetivo)
    # stock_suc - objetivo. Si da negativo, falta stock.
    diff_raw = stock_suc_total_row - stock_obj_ideal_row
    
    # Si sobra (positivo), no pedimos nada (return diff_raw que será positivo o 0)
    if diff_raw >= 0:
        return diff_raw # Se usará para lógica de match pero no para pedir
        
    # Si falta (negativo), calculamos cuánto pedir con LÓGICA SMART
    necesidad_abs = abs(diff_raw)
    
    if fam in ['DONALDSON', 'TURBO']:
        # Donaldson y Turbo mantienen logica simple (o la que prefieras)
        cantidad_a_pedir = ajustar_lote_simple(necesidad_abs, lote)
    else:
        # --- CAMBIO 2: Lógica "Smart Box" ---
        # Si necesito 22 y caja es 12 -> pido 24.
        # Si necesito 30 y caja es 12 -> pido 30.
        cantidad_a_pedir = ajustar_lote_inteligente(necesidad_abs, lote)
    
    # Retornamos negativo porque es "faltante" en la logica de diff
    return -cantidad_a_pedir

def ajustar_lote_simple(cantidad, lote):
    """ Redondeo hacia abajo estándar """
    if pd.isna(lote) or lote <= 0: lote = 1
    return math.floor(cantidad / lote) * lote

def ajustar_lote_inteligente(necesidad, lote):
    """
    CAMBIO 2: Lógica de redondeo flexible.
    - Si la necesidad está 'cerca' de completar caja, redondea a caja.
    - Si está 'lejos' (en el medio), envía cantidad exacta (rompe caja).
    """
    if pd.isna(lote) or lote <= 1: return necesidad
    
    # Calculo cajas ideales (flotante)
    cajas_teoricas = necesidad / lote
    
    # Redondeo al entero más cercano (Nearest Neighbor)
    cajas_redondeadas = round(cajas_teoricas)
    qty_redondeada = cajas_redondeadas * lote
    
    # Calculamos qué tan lejos estamos del redondeo "bonito"
    diferencia = abs(necesidad - qty_redondeada)
    
    # UMBRAL DE TOLERANCIA: 30% del tamaño de la caja
    # Ej: Lote 12. Umbral 3.6.
    # Caso 22: Redondeo 24. Diff 2. (2 < 3.6) -> Pide 24.
    # Caso 25: Redondeo 24. Diff 1. (1 < 3.6) -> Pide 24.
    # Caso 30: Redondeo 24 (Diff 6) o 36 (Diff 6). (6 > 3.6) -> Pide 30 (Rompe caja).
    umbral = lote * 0.30
    
    if diferencia <= umbral:
        # Si el redondeo da 0 pero hay necesidad, forzamos minimo 1 lote 
        # si la necesidad es significativa (> 50% del lote), sino 0.
        if qty_redondeada == 0 and necesidad > (lote * 0.5):
            return lote
        return qty_redondeada
    else:
        return necesidad

def distribuir_stock(df):
    sucursales = ['ba', 'mdz', 'slt']
    
    def calcular_fila(row):
        # 1. Disponibilidad Teórica (basada en cobertura)
        disponible_sf = max(0, row['diff_sf'])
        
        # --- CAMBIO 1: PROTECCIÓN DE INTEGRIDAD SF ---
        # Si SF tiene stock físico >= 1 lote, NO permitimos que el envío baje el stock 
        # a menos de 1 lote (no romper el último juego de SF).
        lote = row['qty_piezas']
        if pd.isna(lote) or lote <= 0: lote = 1
        
        stock_fisico_sf = row['stock_total_sf_fisico']
        
        if lote > 1 and stock_fisico_sf >= lote:
            # Calculamos cuanto podemos dar realmente sin romper el "Stock de Seguridad de Caja"
            # Esto asegura que SF se quede con al menos 1 juego completo si ya la tenía.
            maximo_dable_seguridad = max(0, stock_fisico_sf - lote)
            
            # La disponibilidad real es la menor entre lo que "sobra por cobertura" 
            # y lo que "podemos dar sin romper el ulitmo juego"
            disponible_sf = min(disponible_sf, maximo_dable_seguridad)

        # -----------------------------------------------
        
        necesidades = {}
        total_necesidad = 0
        
        for suc in sucursales:
            faltante = row.get(f'diff_{suc}', 0)
            if faltante < 0:
                necesidad_abs = abs(faltante)
                necesidades[suc] = necesidad_abs
                total_necesidad += necesidad_abs
            else:
                necesidades[suc] = 0
        
        envios = {suc: 0 for suc in sucursales}
        
        if disponible_sf <= 0:
            return pd.Series(envios)
            
        if disponible_sf >= total_necesidad:
            for suc, qty in necesidades.items():
                envios[suc] = qty
            return pd.Series(envios)
            
        if total_necesidad > 0:
            ratio = disponible_sf / total_necesidad
            acumulado = 0
            for suc, qty in necesidades.items():
                if qty > 0:
                    cantidad_teorica = qty * ratio
                    # Aqui usamos floor siempre para no prometer lo que no tenemos al prorratear
                    cantidad_reale = math.floor(cantidad_teorica) 
                    
                    if (acumulado + cantidad_reale) <= disponible_sf:
                        envios[suc] = cantidad_reale
                        acumulado += cantidad_reale
                    else:
                        remanente = disponible_sf - acumulado
                        envios[suc] = remanente
                        acumulado += remanente
        
        return pd.Series(envios)

    cols_envios = df.apply(calcular_fila, axis=1)
    
    for suc in sucursales:
        df[f'final_enviar_{suc}'] = cols_envios[suc]

    return df

# --- NUEVA FUNCIONALIDAD: ANÁLISIS DE DEVOLUCIÓN ---
def calcular_excedentes_sucursales(df, umbral_meses_exceso=0.5):
    """
    Identifica excedentes en sucursales basados en un umbral de cobertura (default 0.5 = 6 meses).
    Calcula qué parte de ese stock es "Sobrante".
    """
    sucursales = ['ba', 'mdz', 'slt']
    
    # 1. Asegurar tipos numéricos para peso y volumen
    for c in ['peso', 'volumen']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 2. Calcular situación de Santa Fe (para ver si el retorno es útil)
    #    Déficit SF = (DemandaTotal * ObjetivoSF) - StockTotalSF
    #    Si Déficit > 0, SF necesita stock.
    #    Asumimos objetivo SF estandar de 0.5 (6 meses) para "necesidad saludable"
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

        # Stock Total Sucursal (Fisico + Transito)
        stock_suc = df[col_stock] + df.get(col_transito, 0)
        demanda_suc = df[col_demanda]
        
        # Cobertura Actual
        cobertura_actual = stock_suc / demanda_suc
        
        # Filtro 1: Solo productos que superan el umbral de cobertura (6 meses)
        # Y que además tengan stock físico (no podemos devolver tránsito fácilmente)
        mask_exceso = (cobertura_actual > umbral_meses_exceso) & (df[col_stock] > 0)
        
        # Cálculo del Excedente (Cantidad a devolver)
        # Cantidad ideal máxima = Demanda * Umbral
        stock_ideal_max = demanda_suc * umbral_meses_exceso
        
        # Excedente teórico
        excedente_teorico = stock_suc - stock_ideal_max
        
        # El excedente real a devolver no puede ser mayor al stock físico disponible
        # (A veces el exceso es teórico por tránsito llegando, pero si no hay físico no se carga camión)
        excedente_real = np.minimum(excedente_teorico, df[col_stock])
        
        # Redondeo hacia abajo (solo devolvemos unidades enteras)
        excedente_final = np.floor(excedente_real)
        
        # Guardamos en DF
        col_excedente = f'excedente_qty_{suc}'
        df[col_excedente] = 0
        df.loc[mask_exceso, col_excedente] = excedente_final
        
        # Limpiar negativos (si floor dio -1 por error de punto flotante)
        df[col_excedente] = df[col_excedente].clip(lower=0)
        
        # Calculo de métricas del excedente
        df[f'excedente_peso_{suc}'] = df[col_excedente] * df['peso']
        df[f'excedente_vol_{suc}'] = df[col_excedente] * df['volumen']
        
        # Indicador de "Match": ¿Este excedente le sirve a SF?
        # Es prioritario si SF tiene déficit de este producto
        df[f'prioridad_retorno_{suc}'] = (df[col_excedente] > 0) & (df['sf_necesita_stock'])

    return df