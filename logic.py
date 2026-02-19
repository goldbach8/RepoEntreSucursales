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

def calcular_coberturas(df, sucursal_origen='sf', cob_origen_meses=6.0, cob_destino_meses=4.0):
    """
    Calcula coberturas y diferencias (Sobra/Falta) de forma dinámica.

    Args:
        df: DataFrame con los datos
        sucursal_origen: Código de sucursal origen ('sf', 'ba', 'mdz', 'slt')
        cob_origen_meses: Cobertura objetivo en meses para la sucursal origen
        cob_destino_meses: Cobertura objetivo en meses para las sucursales destino
    """
    # Convertir meses a años para cálculos internos
    cob_origen_años = cob_origen_meses / 12.0
    cob_destino_años = cob_destino_meses / 12.0

    # 1. Cobertura TOTAL (GLOBAL) - Física
    if 'stock_total' not in df.columns: df['stock_total'] = 0
    df['cobertura_ini_total'] = df['stock_total'] / df['demanda_estimada_total'].replace(0, 0.00001)

    # 2. Preparar stock físico de SF (siempre necesario para cálculos)
    cols_sf_fisico = ['stock_sf', 'stock_aux', 'stock_sv_arg', 'stock_sv_min', 'stock_ns_noa']
    for c in cols_sf_fisico:
        if c not in df.columns: df[c] = 0
    df['stock_total_sf_fisico'] = df[cols_sf_fisico].sum(axis=1)

    # 2.1 Calcular COBERTURA AMPLIADA GLOBAL (incluye todos los tránsitos y envíos entrantes)
    # Esto se usa para limitar correctamente los targets de las sucursales destino

    # Asegurar que existan todas las columnas de tránsito
    cols_transito_global = ['qty_ot_transito_sf', 'qty_ot_transito_ba', 'qty_ot_transito_mdz', 'qty_ot_transito_slt',
                           'qty_sf', 'qty_ba', 'qty_mdz', 'qty_slt']
    for c in cols_transito_global:
        if c not in df.columns: df[c] = 0

    # Stock ampliado global = stock físico total + todos los tránsitos OT + todos los envíos entrantes
    stock_ampliado_global = (
        df['stock_total'] +
        df['qty_ot_transito_sf'] + df['qty_ot_transito_ba'] + df['qty_ot_transito_mdz'] + df['qty_ot_transito_slt'] +
        df['qty_sf'] + df['qty_ba'] + df['qty_mdz'] + df['qty_slt']
    )

    df['cobertura_ampliada_total'] = stock_ampliado_global / df['demanda_estimada_total'].replace(0, 0.00001)

    # 3. Definir todas las sucursales
    todas_sucursales = ['sf', 'ba', 'mdz', 'slt']
    sucursales_destino = [s for s in todas_sucursales if s != sucursal_origen]

    # 4. Calcular para ORIGEN
    col_stock_origen = f'stock_{sucursal_origen}' if sucursal_origen != 'sf' else 'stock_total_sf_fisico'
    col_demanda_origen = f'demanda_estimada_{sucursal_origen}'

    # Obtener stock físico origen
    if sucursal_origen == 'sf':
        stock_fisico_origen = df['stock_total_sf_fisico']
    else:
        stock_fisico_origen = df[col_stock_origen] if col_stock_origen in df.columns else 0

    # COBERTURA AMPLIADA ORIGEN: Incluye stock físico + tránsitos por OT + tránsitos por envío entrante
    # Columna de envío entrante (qty_sf, qty_ba, qty_mdz, qty_slt según sucursal)
    col_envio_entrante = f'qty_{sucursal_origen}'

    # Columna de tránsito por OT (solo para sucursales, no para SF)
    if sucursal_origen == 'sf':
        col_transito_ot = 'qty_ot_transito_sf'  # Para consistencia, aunque SF puede no tener
    elif sucursal_origen == 'slt':
        col_transito_ot = 'qty_ot_transito_slt'
    else:
        col_transito_ot = f'qty_ot_transito_{sucursal_origen}'

    # Stock ampliado = físico + tránsito OT + envío entrante
    stock_ampliado_origen = (
        stock_fisico_origen +
        df.get(col_transito_ot, 0) +
        df.get(col_envio_entrante, 0)
    )

    # Cobertura ampliada (para referencia y visualización)
    df[f'cobertura_ampliada_{sucursal_origen}'] = stock_ampliado_origen / df[col_demanda_origen].replace(0, 0.00001)

    # Cobertura inicial (solo físico + tránsito OT, sin envío entrante)
    stock_inicial_origen = stock_fisico_origen + df.get(col_transito_ot, 0)
    df[f'cobertura_ini_{sucursal_origen}'] = stock_inicial_origen / df[col_demanda_origen].replace(0, 0.00001)

    # Objetivo real origen (usar cobertura ampliada global)
    df[f'target_{sucursal_origen}_eff'] = np.minimum(cob_origen_años, df['cobertura_ampliada_total'])
    stock_obj_origen = df[col_demanda_origen] * df[f'target_{sucursal_origen}_eff']

    # Diferencia usando STOCK AMPLIADO (considera envío entrante para decidir si hay excedente)
    df[f'diff_{sucursal_origen}'] = stock_ampliado_origen - stock_obj_origen

    # Guardar columnas auxiliares para distribuir_stock
    df[f'_stock_fisico_{sucursal_origen}'] = stock_fisico_origen
    df[f'_stock_ampliado_{sucursal_origen}'] = stock_ampliado_origen

    # 5. Calcular para DESTINOS
    for suc_destino in sucursales_destino:
        col_stock = f'stock_{suc_destino}'

        # Columna de tránsito OT: qty_ot_transito_* para todas las sucursales
        if suc_destino == 'sf':
            col_stock = 'stock_total_sf_fisico'
            col_transito = 'qty_ot_transito_sf'
        else:
            col_transito = f'qty_ot_transito_{suc_destino}'

        stk = df[col_stock] if col_stock in df.columns else 0
        trs = df.get(col_transito, 0)

        stock_suc_total = stk + trs
        col_demanda_local = f'demanda_estimada_{suc_destino}'

        df[f'cobertura_ini_{suc_destino}'] = stock_suc_total / df[col_demanda_local].replace(0, 0.00001)

        # Usar cobertura ampliada global para calcular target efectivo
        target_suc_eff = np.minimum(cob_destino_años, df['cobertura_ampliada_total'])
        stock_obj_ideal = df[col_demanda_local] * target_suc_eff

        # Diferencia Real Sucursal (Float)
        df[f'diff_{suc_destino}'] = stock_suc_total - stock_obj_ideal

    return df

def distribuir_stock(df, sucursal_origen='sf'):
    """
    Define los envíos aplicando lógica de cajas (Filtros) y juegos (No Filtros).
    Corrige la ineficiencia de remanentes en escenarios de escasez.

    Args:
        df: DataFrame con los datos calculados
        sucursal_origen: Código de sucursal origen ('sf', 'ba', 'mdz', 'slt')
    """
    # Determinar sucursales destino dinámicamente
    todas_sucursales = ['sf', 'ba', 'mdz', 'slt']
    sucursales_destino = [s for s in todas_sucursales if s != sucursal_origen]

    # Familias consideradas "Filtros" para lógica de cajas
    familias_filtros = ['DONALDSON', 'TURBO', 'KTN'] 
    
    def calcular_fila(row):
        qty_p = row['qty_piezas']
        if pd.isna(qty_p) or qty_p <= 0: qty_p = 1

        fam = row['familia_logica']
        es_filtro = fam in familias_filtros

        # --- 1. DISPONIBILIDAD EN SUCURSAL ORIGEN ---
        # El diff ya está calculado con stock ampliado (incluye envío entrante)
        diff_origen_ampliado = row[f'diff_{sucursal_origen}']

        # Obtener stocks de las columnas auxiliares
        stock_fisico_origen = row.get(f'_stock_fisico_{sucursal_origen}', 0)
        demanda_origen = row[f'demanda_estimada_{sucursal_origen}']

        # RESTRICCIÓN CLAVE: Retener stock para cubrir 1 mes hasta que llegue el envío entrante
        cobertura_minima_años = 1.0 / 12.0  # 1 mes = 0.0833 años
        demanda_1_mes = demanda_origen * cobertura_minima_años

        if diff_origen_ampliado > 0:
            # Hay excedente según cobertura ampliada
            if es_filtro:
                # Lógica Filtros: Retener demanda de 1 mes
                # Máximo a enviar = Stock_Físico - Demanda_1_Mes
                stock_minimo_retencion = demanda_1_mes
                max_disponible_fisico = max(0, stock_fisico_origen - stock_minimo_retencion)
                disponible_origen = math.floor(min(diff_origen_ampliado, max_disponible_fisico))

            else:
                # Lógica Kits (No Filtros): Retener kits completos para 1 mes
                # Calcular kits necesarios para cubrir 1 mes de demanda
                kits_para_1_mes = math.ceil(demanda_1_mes / qty_p)

                # Retener al menos 1 juego completo, o lo que se necesite para 1 mes
                kits_necesarios_minimo = max(1, kits_para_1_mes)
                stock_retencion_final = kits_necesarios_minimo * qty_p

                # Disponible desde stock físico
                max_disponible_fisico = max(0, stock_fisico_origen - stock_retencion_final)
                disponible_teorico = min(diff_origen_ampliado, max_disponible_fisico)
                disponible_origen = max(0, int(disponible_teorico))

        else:
            disponible_origen = 0

        # Seguridad física final: nunca enviar más que el stock físico
        disponible_origen = min(disponible_origen, stock_fisico_origen)

        envios_deseados = {}
        total_deseado = 0

        # --- 2. NECESIDAD SUCURSALES DESTINO (TECHO DEL FALTANTE) ---
        for suc_destino in sucursales_destino:
            diferencia_real = row.get(f'diff_{suc_destino}', 0)

            if diferencia_real < 0:
                falta_base = math.ceil(abs(diferencia_real))
                qty_a_pedir = 0

                if es_filtro:
                    qty_a_pedir = calcular_qty_filtros(falta_base, qty_p)
                else:
                    # Determinar columnas según sucursal destino
                    if suc_destino == 'sf':
                        col_stock = 'stock_total_sf_fisico'
                        col_trans = 'qty_ot_transito_sf'
                    else:
                        col_stock = f'stock_{suc_destino}'
                        col_trans = f'qty_ot_transito_{suc_destino}'

                    stock_suc_actual = row.get(col_stock, 0) + row.get(col_trans, 0)
                    qty_a_pedir = calcular_qty_kits(falta_base, stock_suc_actual, qty_p)

                envios_deseados[suc_destino] = qty_a_pedir
                total_deseado += qty_a_pedir
            else:
                envios_deseados[suc_destino] = 0

        # --- 3. DISTRIBUCIÓN ---
        envios_finales = {suc: 0 for suc in sucursales_destino}

        if disponible_origen <= 0:
            return pd.Series(envios_finales)

        if disponible_origen >= total_deseado:
            for suc, qty in envios_deseados.items():
                envios_finales[suc] = qty
            return pd.Series(envios_finales)

        # Escasez: Prorratear con corrección de remanentes
        if total_deseado > 0:
            ratio = disponible_origen / total_deseado

            # A) Asignación proporcional base (suelo)
            for suc, qty_deseada in envios_deseados.items():
                if qty_deseada > 0:
                    cant_prop = math.floor(qty_deseada * ratio)
                    envios_finales[suc] = cant_prop

            # B) Distribuir el remanente (lo que sobró por redondear hacia abajo)
            total_asignado = sum(envios_finales.values())
            remanente = disponible_origen - total_asignado

            if remanente > 0:
                # Candidatos: Sucursales que pidieron y aún no recibieron todo
                candidatos = []
                for suc in sucursales_destino:
                    if envios_deseados[suc] > 0:
                        falta_para_deseado = envios_deseados[suc] - envios_finales[suc]
                        if falta_para_deseado > 0:
                            # Prioridad: Diff más negativo (mayor escasez)
                            diff_val = row.get(f'diff_{suc}', 0)
                            candidatos.append({'suc': suc, 'diff': diff_val})

                # Ordenar por mayor necesidad (diff más negativo primero)
                candidatos.sort(key=lambda x: x['diff'])

                # Repartir 1 a 1 en orden de prioridad hasta agotar remanente
                idx = 0
                while remanente > 0 and candidatos:
                    # Usamos módulo para dar vuelta a la lista si sobra mucho (raro)
                    cand = candidatos[idx % len(candidatos)]
                    suc_cand = cand['suc']

                    # Verificación final para no dar más de lo deseado (opcional en escasez extrema, pero prolijo)
                    if envios_finales[suc_cand] < envios_deseados[suc_cand]:
                        envios_finales[suc_cand] += 1
                        remanente -= 1

                    idx += 1

        return pd.Series(envios_finales)

    cols_envios = df.apply(calcular_fila, axis=1)
    for suc in sucursales_destino:
        df[f'final_enviar_{suc}'] = cols_envios[suc]

    return df

def calcular_qty_filtros(necesidad, lote):
    """
    Regla Filtros:
    - Caja 6: Completar si tengo 4 o 5 (falta 1 o 2).
    - Caja 12: Completar si tengo 9, 10, 11 (falta 1, 2 o 3).
    """
    if lote <= 1: return necesidad

    resto = necesidad % lote
    if resto == 0: return necesidad
        
    adicional_para_cerrar = lote - resto
    
    if lote == 6 and adicional_para_cerrar <= 2:
        return necesidad + adicional_para_cerrar
    elif lote == 12 and adicional_para_cerrar <= 3:
        return necesidad + adicional_para_cerrar

    return necesidad

def calcular_qty_kits(necesidad_base, stock_actual, lote):
    """
    Regla Kits (No Filtros):
    (Stock_Actual + Envio) debe ser múltiplo de Lote (Juego).
    """
    if lote <= 1: return necesidad_base
    
    objetivo_minimo = stock_actual + necesidad_base
    kits_necesarios = math.ceil(objetivo_minimo / lote)
    stock_final_deseado = kits_necesarios * lote
    
    envio_calculado = stock_final_deseado - stock_actual
    return max(0, int(envio_calculado))

def calcular_excedentes_sucursales(df, umbral_meses_exceso=0.5):
    """ Identifica excedentes en sucursales. """
    sucursales = ['ba', 'mdz', 'slt']
    for c in ['peso', 'volumen']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Contexto SF
    obj_sf = 0.5 
    stock_sf_total = df['stock_total_sf_fisico'] + df.get('qty_sf', 0)
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