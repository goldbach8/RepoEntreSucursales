import streamlit as st
import pandas as pd
import logic
import utils
import io # Necesario para manejar el archivo binario de Excel

# Configuración de página con un layout más amplio
st.set_page_config(
    page_title="Gestión de Stock Sucursales", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Personalizado para UI Moderna ---
st.markdown("""
    <style>
    /* Estilo general del fondo y textos */
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', sans-serif; }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] { 
        background-color: #ffffff; 
        border-right: 1px solid #e9ecef;
    }
    
    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem; color: #6c757d; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; color: #2c3e50; font-weight: 600; }
    
    /* Botones */
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        font-weight: 600;
        transition: all 0.3s ease;
    }
    /* Botón Principal (Procesar) - Rojo corporativo o acento */
    .primary-btn button {
        background-color: #ff4b4b; 
        color: white; 
        box-shadow: 0 4px 6px rgba(255, 75, 75, 0.2);
    }
    .primary-btn button:hover {
        background-color: #e63939;
        transform: translateY(-2px);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 8px 8px 0px 0px;
        border: 1px solid #e9ecef;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eef2f7;
        color: #ff4b4b;
        border-bottom: 2px solid #ff4b4b;
    }
    
    /* Alertas custom */
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border: 1px solid transparent;
    }
    .alert-info { background-color: #cce5ff; border-color: #b8daff; color: #004085; }
    .alert-success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; }
    .alert-warning { background-color: #fff3cd; border-color: #ffeeba; color: #856404; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAR SESSION STATE PARA PERSISTENCIA ---
if 'data_calculada' not in st.session_state:
    st.session_state.data_calculada = None
if 'modo_calculado' not in st.session_state:
    st.session_state.modo_calculado = None

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4143/4143163.png", width=60) # Placeholder icon
    st.title("Gestión Stock")
    
    # --- SELECTOR DE MODO ---
    st.markdown("### 🔄 Modo de Análisis")
    modo_analisis = st.selectbox(
        "Seleccione Objetivo:",
        ["Reposición (Envío)", "Devolución (Sobrantes)"],
        index=0,
        help="Elija 'Reposición' para calcular envíos desde SF. Elija 'Devolución' para detectar excesos en sucursales."
    )
    
    st.divider()
    st.header("Configuración")

    # Sección 1: Filtros de Datos
    st.subheader("🛠️ Filtros de Datos")
    with st.expander("Opciones de Limpieza", expanded=False):
        ignorar_inhabilitados = st.checkbox("Ignorar Inhabilitados", value=True)
        ignorar_sin_stock = st.checkbox("Ignorar Sin Stock", value=True)
        ignorar_sin_demanda = st.checkbox("Ignorar Sin Demanda", value=True)
        # NUEVO FILTRO DNS
        ignorar_dns = st.checkbox("Ignorar DNS (Inmovilizado/A Demanda)", value=True, help="Excluye items con Grupo Stock 'DNS - A Demanda' o 'DNS - Inmovilizado'")

    # Sección 2: Filtro de Familias
    st.subheader("🗂️ Familias Lógicas")
    familias_opciones = ['GET', 'RODAJE', 'DONALDSON', 'TURBO', 'KTN', 'REPUESTOS', 'OTROS']
    familias_seleccionadas = st.multiselect(
        "Seleccionar Familias:",
        options=familias_opciones,
        default=familias_opciones
    )

    st.divider()

    # Parametros según modo
    if modo_analisis == "Reposición (Envío)":
        st.subheader("📊 Lógica de Demanda")
        metodo_demanda = st.radio(
            "Método Estimación:", 
            ('A', 'B'), 
            index=1, # Default B
            horizontal=True,
            help="**Método A (Teórico):** Basado en parque de máquinas (Population) y coeficientes de familia.\n\n**Método B (Histórico):** Basado en histórico de ventas/reemplazos reciente (Recomendado)."
        )

        st.subheader("🎯 Coberturas (En años)")
        cob_sf = st.number_input("Objetivo Santa Fe", value=0.5, step=0.05, help="0.5 = 6 meses")
        st.markdown("<small>Objetivos Sucursales</small>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        cob_ba = c1.number_input("BA", value=0.33, step=0.05)
        cob_mdz = c2.number_input("MDZ", value=0.33, step=0.05)
        cob_slt = c3.number_input("SLT", value=0.33, step=0.05)
        
    else:
        # Parametros modo Devolución
        st.subheader("📊 Parámetros Devolución")
        metodo_demanda = st.radio(
            "Método Estimación (Base):", 
            ('A', 'B'), 
            index=1, # Default B
            horizontal=True,
            help="**Método A:** Cálculo Teórico (Parque).\n**Método B:** Cálculo Histórico (Rotación)."
        )
        
        # CAMBIO: Parametrización del umbral de exceso
        st.markdown("---")
        umbral_devolucion = st.number_input(
            "Umbral de Exceso (Ratio)", 
            value=0.5, 
            step=0.05, 
            min_value=0.1,
            help="Cobertura a partir de la cual se considera stock sobrante. 0.5 equivale a 6 meses (0.5 años)."
        )
        meses_equiv = umbral_devolucion * 12
        st.caption(f"ℹ️ Se considerará sobrante todo stock que supere los **{meses_equiv:.1f} meses** de cobertura.")

# --- ÁREA PRINCIPAL ---

col_header_1, col_header_2 = st.columns([3, 1])
with col_header_1:
    if modo_analisis == "Reposición (Envío)":
        st.title("📦 Reposiciones: SF ➔ Sucursales")
        st.markdown("Cálculo de envíos para abastecer la red.")
    else:
        st.title("↩️ Devoluciones: Sucursales ➔ SF")
        st.markdown("Análisis de stock inmovilizado y oportunidades de retorno.")

# Carga de Archivos
with st.container():
    st.write("") 
    col_upload, col_template = st.columns([3, 1], gap="medium")
    
    with col_upload:
        uploaded_file = st.file_uploader("Sube tu archivo CSV maestro:", type=['csv'], label_visibility="collapsed")
        
    with col_template:
        st.write("") 
        st.download_button(
            label="📄 Descargar Plantilla", 
            data=utils.generar_csv_ejemplo(), 
            file_name="template_reposicion.csv", 
            mime="text/csv"
        )

if not uploaded_file:
    st.info("👋 **Bienvenido!** Para comenzar, sube el archivo CSV de inventario.")

else:
    df = utils.cargar_datos(uploaded_file)
    
    if df is not None:
        faltantes = utils.validar_columnas(df)
        if faltantes:
            st.error(f"❌ **Error de Formato:** Faltan columnas: {', '.join(faltantes)}")
        else:
            # APLICACION DE FILTROS (Incuyendo DNS)
            df = utils.aplicar_filtros_avanzados(df, ignorar_inhabilitados, ignorar_sin_stock, ignorar_sin_demanda, ignorar_dns)
            st.success(f"✅ Archivo cargado: **{len(df)} registros**.")
            st.divider()
            
            # Botón único de proceso
            col_proc_1, col_proc_2, col_proc_3 = st.columns([1, 2, 1])
            with col_proc_2:
                btn_label = "🚀 CALCULAR ENVÍOS" if modo_analisis == "Reposición (Envío)" else "🔍 ANALIZAR SOBRANTES"
                process_clicked = st.button(btn_label, type="primary", use_container_width=True)

            # --- LÓGICA DE CÁLCULO ---
            if process_clicked:
                if len(df) == 0:
                    st.error("⚠️ No hay datos para procesar.")
                else:
                    with st.spinner('🔄 Procesando lógica de negocio...'):
                        
                        # 1. Cálculos Comunes (W y Demanda)
                        df_proc = logic.calcular_parametros_w(df)
                        
                        # Filtro Familias
                        if familias_seleccionadas:
                            df_proc = df_proc[df_proc['familia_logica'].isin(familias_seleccionadas)]
                        
                        if len(df_proc) == 0:
                            st.warning("⚠️ No hay registros para las familias seleccionadas.")
                            st.session_state.data_calculada = None # Limpiar si falla
                        else:
                            df_proc = logic.estimar_demanda(df_proc, metodo_demanda)
                            
                            # ----------------------------------------------------
                            #                 MODO REPOSICIÓN
                            # ----------------------------------------------------
                            if modo_analisis == "Reposición (Envío)":
                                df_proc = logic.calcular_coberturas(df_proc, cob_sf, cob_ba, cob_mdz, cob_slt)
                                df_final = logic.distribuir_stock(df_proc)
                                
                                # Cálculos Extra Visuales
                                for col in ['qty_ee_transito_sf', 'qty_ot_transito_sf']:
                                    if col not in df_final.columns: df_final[col] = 0
                                stock_ampliado_sf = df_final['stock_total_sf_fisico'] + df_final['qty_ee_transito_sf'] + df_final['qty_ot_transito_sf']
                                
                                df_final['cobertura_ampliada_sf'] = stock_ampliado_sf / df_final['demanda_estimada_sf']

                                # --- CÁLCULO DE COBERTURAS FINALES (Post Envío) ---
                                for suc in ['ba', 'mdz', 'slt']:
                                    col_stock = f'stock_{suc}'
                                    col_transito = f'qty_transito_{suc}' if suc != 'slt' else 'qty_ot_transito_slt'
                                    col_envio = f'final_enviar_{suc}'
                                    col_demanda = f'demanda_estimada_{suc}'
                                    
                                    # Stock Final = Stock Actual + Transito + Envio Nuevo
                                    stock_final = df_final[col_stock] + df_final.get(col_transito, 0) + df_final[col_envio]
                                    
                                    # Evitar division por cero (demanda 0 -> inf)
                                    df_final[f'cobertura_fin_{suc}'] = stock_final / df_final[col_demanda].replace(0, 0.0001)

                                # --- LIMPIEZA DE DECIMALES ---
                                # Ajuste solicitado: NO convertir 'diff' a int, sino redondear a 2 decimales.
                                for col in df_final.columns:
                                    # Criterio: Numerico y nombre específico. QUITO 'diff' de la lista de enteros.
                                    condicion_enteros = any(x in col for x in ['qty', 'qpres', 'qrem', 'stock', 'final_enviar', 'transito'])
                                    
                                    # Excepciones
                                    no_es_peso_vol = 'peso' not in col and 'volumen' not in col and 'cobertura' not in col
                                    
                                    if pd.api.types.is_numeric_dtype(df_final[col]):
                                        # Si es de tipo entero (qty, stock, etc) -> Int
                                        if condicion_enteros and no_es_peso_vol:
                                            df_final[col] = df_final[col].fillna(0).round(0).astype(int)
                                        
                                        # Si es Sobra/Falta (diff) -> Float con 2 decimales
                                        elif 'diff' in col:
                                            df_final[col] = df_final[col].fillna(0).round(2)

                                # GUARDAR EN SESSION STATE
                                st.session_state.data_calculada = df_final
                                st.session_state.modo_calculado = "Reposición (Envío)"

                            # ----------------------------------------------------
                            #                 MODO DEVOLUCIÓN
                            # ----------------------------------------------------
                            else:
                                # 1. Calcular fisicos SF necesarios para el análisis de "Match"
                                cols_sf_fisico = ['stock_sf', 'stock_aux', 'stock_sv_arg', 'stock_sv_min', 'stock_ns_noa']
                                for c in cols_sf_fisico: 
                                    if c not in df_proc.columns: df_proc[c] = 0
                                df_proc['stock_total_sf_fisico'] = df_proc[cols_sf_fisico].sum(axis=1)

                                # 2. Lógica de Excedentes
                                df_dev = logic.calcular_excedentes_sucursales(df_proc, umbral_meses_exceso=umbral_devolucion)
                                
                                # GUARDAR EN SESSION STATE
                                st.session_state.data_calculada = df_dev
                                st.session_state.modo_calculado = "Devolución (Sobrantes)"


            # --- VISUALIZACIÓN (SE EJECUTA SI HAY DATOS EN SESIÓN) ---
            if st.session_state.data_calculada is not None and st.session_state.modo_calculado == modo_analisis:
                
                # REPOSICIÓN
                if modo_analisis == "Reposición (Envío)":
                    df_final = st.session_state.data_calculada
                    
                    # --- PREPARACIÓN DE DATOS PARA VISTA PRINCIPAL ---
                    column_map = {
                        'familia_logica': 'Familia Logica',
                        'familia': 'Familia',
                        'subfamilia': 'Subfamilia',
                        'subfamilia2': 'Subfamilia2',
                        'grupo_stock': 'Grupo Stock',
                        'codigo': 'Codigo',
                        'descripcion': 'Descripcion',
                        'descripcion2': 'Descripcion2',
                        'qty_piezas': 'qty piezas',
                        'peso': 'peso',
                        'volumen': 'volumen',
                        'qpres_total': 'q pres total',
                        'qrem_total': 'q rem total',
                        'Wp': 'Wproducto',
                        'Wf': 'Wfamilia',
                        'demanda_estimada_total': 'd est total',
                        'stock_total': 'stock total',
                        'cobertura_ini_total': 'cobertura total',
                        # SF
                        'qpressf': 'q pres SF',
                        'qremsf': 'Q rem SF',
                        'demanda_estimada_sf': 'D est SF',
                        'stock_total_sf_fisico': 'Stock SF Final', 
                        'stock_sf': 'Stock SF',
                        'stock_aux': 'Stock Aux',
                        'stock_sv_arg': 'Stock SV ARG',
                        'stock_sv_min': 'Stock SV MIN',
                        'stock_ns_noa': 'Stock NS NOA',
                        'qty_ee_transito_sf': 'Transito EE SF',
                        'qty_ot_transito_sf': 'Transito OT SF',
                        'cobertura_ini_sf': 'cobertura inicial SF',
                        'cobertura_ampliada_sf': 'Cobertura Ampliada SF',
                        'diff_sf': 'Sobra/Falta SF',
                        # BA
                        'qpresba': 'QPresBA',
                        'qremba': 'QRemBA',
                        'demanda_estimada_ba': 'D.EST BA',
                        'stock_ba': 'Stock BA',
                        'qty_transito_ba': 'Transito BA',
                        'cobertura_ini_ba': 'cobertura inicial BA',
                        'diff_ba': 'Sobra / Falta BA',
                        'final_enviar_ba': 'q enviar BA',
                        # MDZ
                        'qpresmdz': 'QPresMDZ',
                        'qremmdz': 'QRemMDZ',
                        'demanda_estimada_mdz': 'D.EST MDZ',
                        'stock_mdz': 'Stock MDZ',
                        'qty_transito_mdz': 'Transito MDZ',
                        'cobertura_ini_mdz': 'cobertura inicial MDZ',
                        'diff_mdz': 'Sobra / Falta MDZ',
                        'final_enviar_mdz': 'q enviar MDZ',
                        # SLT
                        'qpresslt': 'QPresSLT',
                        'qremslt': 'QRemSLT',
                        'demanda_estimada_slt': 'D.EST SLT',
                        'stock_slt': 'Stock SLT',
                        'qty_ot_transito_slt': 'Transito OT SLT',
                        'cobertura_ini_slt': 'cobertura inicial SLT',
                        'diff_slt': 'Sobra / Falta SLT',
                        'final_enviar_slt': 'q enviar SLT'
                    }
                    
                    final_order = [
                        'Familia Logica', 'Familia', 'Subfamilia', 'Subfamilia2', 'Grupo Stock', 'Codigo', 'Descripcion', 'Descripcion2', 
                        'qty piezas', 'peso', 'volumen', 'q pres total', 'q rem total', 'Wproducto', 'Wfamilia', 'd est total', 
                        'stock total', 'cobertura total', 
                        'q pres SF', 'Q rem SF', 'D est SF', 
                        'Stock SF', 'Stock Aux', 'Stock SV ARG', 'Stock SV MIN', 'Stock NS NOA', 
                        'Transito EE SF', 'Transito OT SF', 
                        'Stock SF Final', 
                        'cobertura inicial SF', 'Cobertura Ampliada SF', 
                        'Sobra/Falta SF',
                        'QPresBA', 'QRemBA', 'D.EST BA', 'Stock BA', 'Transito BA', 'cobertura inicial BA', 'Sobra / Falta BA', 'q enviar BA',
                        'QPresMDZ', 'QRemMDZ', 'D.EST MDZ', 'Stock MDZ', 'Transito MDZ', 'cobertura inicial MDZ', 'Sobra / Falta MDZ', 'q enviar MDZ',
                        'QPresSLT', 'QRemSLT', 'D.EST SLT', 'Stock SLT', 'Transito OT SLT', 'cobertura inicial SLT', 'Sobra / Falta SLT', 'q enviar SLT'
                    ]
                    
                    # Relleno de columnas faltantes visuales
                    for col_internal, col_final in column_map.items():
                        if col_internal not in df_final.columns:
                            df_final[col_internal] = 0 

                    df_view = df_final.rename(columns=column_map)
                    cols_existentes = [c for c in final_order if c in df_view.columns]
                    df_view = df_view[cols_existentes]
                    
                    # --- NUEVA PLANILLA RESUMEN ---
                    # Crear DF especifico para el pedido "Resumen"
                    cols_resumen_map = {
                        'codigo': 'Código',
                        'descripcion': 'Descripción',
                        'qty_piezas': 'qty piezas',
                        'qpres_total': 'QPres Total',
                        'qrem_total': 'QRem Total',
                        'demanda_estimada_total': 'D.EST Total',
                        'stock_total': 'Stock Total',
                        'cobertura_ini_total': 'Cobertura Anual',
                        # SF
                        'qpressf': 'QPresSF',
                        'qremsf': 'QRemSF',
                        'demanda_estimada_sf': 'D.EST SF',
                        'stock_total_sf_fisico': 'STOCK SF FINAL',
                        'diff_sf': 'Sobra / Falta SF',
                        # BA
                        'qpresba': 'QPresBA',
                        'qremba': 'QRemBA',
                        'demanda_estimada_ba': 'D.EST BA',
                        'stock_ba': 'Stock BA',
                        'diff_ba': 'Sobra / Falta BA',
                        'final_enviar_ba': 'Cant. Enviar BA',
                        'cobertura_ini_ba': 'Cob. Ini BA',
                        'cobertura_fin_ba': 'Cob. Fin BA',
                        # MDZ
                        'qpresmdz': 'QPresMDZ',
                        'qremmdz': 'QRemMDZ',
                        'demanda_estimada_mdz': 'D.EST MDZ',
                        'stock_mdz': 'STOCK MDZ FINAL',
                        'diff_mdz': 'Sobra / Falta MDZ',
                        'final_enviar_mdz': 'Cant. Enviar MDZ',
                        'cobertura_ini_mdz': 'Cob. Ini MDZ',
                        'cobertura_fin_mdz': 'Cob. Fin MDZ',
                        # SLT
                        'qpresslt': 'QPresSLT',
                        'qremslt': 'QRemSLT',
                        'demanda_estimada_slt': 'D.EST SALTA',
                        'stock_slt': 'Stock SLT',
                        'diff_slt': 'Sobra / Falta SLT',
                        'final_enviar_slt': 'Cant. Enviar SLT',
                        'cobertura_ini_slt': 'Cob. Ini SLT',
                        'cobertura_fin_slt': 'Cob. Fin SLT'
                    }
                    
                    # Extraer datos para resumen usando df_final original
                    df_resumen = pd.DataFrame()
                    for col_orig, col_dest in cols_resumen_map.items():
                        if col_orig in df_final.columns:
                            # Si es cobertura o diferencia, redondeamos a 2 decimales para que se vea bien
                            if 'cobertura' in col_orig or 'diff' in col_orig:
                                df_resumen[col_dest] = df_final[col_orig].fillna(0).round(2)
                            else:
                                df_resumen[col_dest] = df_final[col_orig]
                        else:
                            df_resumen[col_dest] = 0

                    # ---------------------------------
                    
                    st.markdown("### 📊 Tablero de Resultados")
                    
                    # Asegurar numéricos para cálculos de totales
                    df_view['peso'] = pd.to_numeric(df_view['peso'], errors='coerce').fillna(0)
                    df_view['volumen'] = pd.to_numeric(df_view['volumen'], errors='coerce').fillna(0)
                    
                    # Pre-cálculo de columnas de totales para resumen
                    for suc in ['BA', 'MDZ', 'SLT']:
                        col_envio = f'q enviar {suc}'
                        df_view[f'peso_total_{suc}'] = df_view[col_envio] * df_view['peso']
                        df_view[f'vol_total_{suc}'] = df_view[col_envio] * df_view['volumen']

                        # Lógica de riesgo
                        col_demanda_orig = f'demanda_estimada_{suc.lower()}'
                        col_stock_orig = f'stock_{suc.lower()}'
                        col_transito_orig = f'qty_transito_{suc.lower()}' if suc.lower() != 'slt' else 'qty_ot_transito_slt'
                        col_enviar_orig = f'final_enviar_{suc.lower()}'
                        
                        stock_actual = df_final[col_stock_orig] + df_final.get(col_transito_orig, 0)
                        demanda = df_final[col_demanda_orig]
                        
                        cob_antes = stock_actual / demanda
                        cob_despues = (stock_actual + df_final[col_enviar_orig]) / demanda
                        
                        df_view[f'risk_antes_{suc}'] = cob_antes < 0.0833 
                        df_view[f'salvados_{suc}'] = (df_view[f'risk_antes_{suc}']) & (cob_despues >= 0.0833)

                    # PREPARAR DATA PARA DESCARGA (Limpieza de columnas visuales)
                    cols_mostrar = [c for c in df_view.columns if 'risk_' not in c and 'salvados_' not in c and 'peso_total' not in c and 'vol_total' not in c]
                    df_display_final = df_view[cols_mostrar]

                    # --- TABS DE SUCURSALES ---
                    sucursales_view = ['BA', 'MDZ', 'SLT']
                    tabs = st.tabs([f"📍 {s}" for s in sucursales_view])
                    
                    for i, suc in enumerate(sucursales_view):
                        with tabs[i]:
                            col_envio = f'q enviar {suc}'
                            df_suc = df_view[df_view[col_envio] > 0]
                            
                            # Tarjetas de Métricas (KPIs)
                            with st.container():
                                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                                
                                qty_total = df_suc[col_envio].sum()
                                prod_distintos = df_suc['Codigo'].nunique()
                                peso_tot = df_suc[f'peso_total_{suc}'].sum()
                                vol_tot = df_suc[f'vol_total_{suc}'].sum()
                                
                                kpi1.metric("📦 Unidades a Enviar", f"{qty_total:,.0f}")
                                kpi2.metric("🔢 SKUs Distintos", f"{prod_distintos}")
                                kpi3.metric("⚖️ Peso Total", f"{peso_tot:,.2f} kg")
                                kpi4.metric("🧊 Volumen Total", f"{vol_tot:,.2f} m³")
                            
                            st.write("") # Spacer
                            
                            # Alertas de Stock
                            kriticos = df_view[df_view[f'risk_antes_{suc}']].shape[0]
                            cubiertos = df_view[df_view[f'salvados_{suc}']].shape[0]
                            
                            if kriticos > 0:
                                msg_riesgo = f"""
                                <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba; color: #856404;">
                                    ⚠️ <strong>Alerta de Cobertura:</strong> Hay <b>{kriticos}</b> productos con stock crítico (<1 mes). 
                                    Con este envío, <b>{cubiertos}</b> de ellos recuperarán niveles saludables.
                                </div>
                                """
                                st.markdown(msg_riesgo, unsafe_allow_html=True)
                            else:
                                st.success("✅ Todos los productos tienen cobertura saludable antes del envío.")
                            
                            st.write("")
                            st.markdown("##### 📋 Detalle por Familia")
                            
                            # Tabla Resumen Agrupada
                            group_cols = ['Familia Logica']
                            df_grp = df_suc.groupby(group_cols).agg({
                                col_envio: 'sum',
                                f'peso_total_{suc}': 'sum',
                                f'vol_total_{suc}': 'sum'
                            }).reset_index()
                            
                            df_grp.columns = ['Familia', 'Cantidad', 'Peso (kg)', 'Volumen (m3)']
                            
                            st.dataframe(
                                df_grp.style.format({
                                    'Cantidad': '{:,.0f}',
                                    'Peso (kg)': '{:.2f}', 
                                    'Volumen (m3)': '{:.2f}'
                                }), 
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            st.caption("ℹ️ *Nota: Totales parciales basados en la información de peso y volumen disponible en el maestro.*")
                            
                            # ==========================================
                            #       PLANILLA DETALLADA (EXPANDER)
                            # ==========================================
                            st.write("")
                            with st.expander("📑 Ver Planilla Detallada Completa", expanded=False):
                                st.markdown("Vista previa de los datos procesados. Utilice el botón inferior para descargar el Excel/CSV completo.")
                                
                                # Definición de grupos para coloreado
                                cols_total = ['q pres total', 'q rem total', 'Wproducto', 'Wfamilia', 'd est total', 'stock total', 'cobertura total']
                                cols_sf = [c for c in df_display_final.columns if 'SF' in c or c in ['Stock Aux', 'Stock SV ARG', 'Stock SV MIN', 'Stock NS NOA']]
                                cols_ba = [c for c in df_display_final.columns if 'BA' in c]
                                cols_mdz = [c for c in df_display_final.columns if 'MDZ' in c]
                                cols_slt = [c for c in df_display_final.columns if 'SLT' in c]
                                
                                # Validar existencia
                                cols_total = [c for c in cols_total if c in df_display_final.columns]
                                cols_sf = [c for c in cols_sf if c in df_display_final.columns]

                                format_dict = {c: "{:.2f}" for c in df_display_final.select_dtypes(include='float').columns}

                                # Lógica de estilo
                                def highlight_wp(row):
                                    col_wp = 'Wproducto'
                                    col_wf = 'Wfamilia'
                                    if col_wp in row.index and col_wf in row.index:
                                        try:
                                            val_wp = float(row[col_wp])
                                            val_wf = float(row[col_wf])
                                            if val_wp < val_wf:
                                                return ['background-color: #ffb3b3' if c == col_wp else '' for c in row.index]
                                        except:
                                            pass
                                    return ['' for c in row.index]

                                pd.set_option("styler.render.max_elements", 5000000)
                                
                                # Aplicar estilos
                                styled_df = df_display_final.head(1000).style.apply(highlight_wp, axis=1)\
                                    .set_properties(subset=cols_sf, **{'background-color': '#fff0f0'})\
                                    .set_properties(subset=cols_ba, **{'background-color': '#e6f3ff'})\
                                    .set_properties(subset=cols_mdz, **{'background-color': '#fff0e6'})\
                                    .set_properties(subset=cols_slt, **{'background-color': '#f0ffe6'})\
                                    .format(format_dict)
                                
                                st.dataframe(styled_df, use_container_width=True)
                                st.caption("Mostrando primeras 1000 filas.")

                    # ==========================================
                    #       BOTONES DE DESCARGA (FUERA DEL LOOP)
                    # ==========================================
                    st.divider()
                    st.markdown("### 📥 Descargas Globales")
                    c_down1, c_down2, c_down3 = st.columns([1, 1, 1])
                    
                    # Descarga Resumen (EXCEL)
                    with c_down1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_resumen.to_excel(writer, index=False, sheet_name='Resumen')
                        
                        st.download_button(
                            label="📋 DESCARGAR RESUMEN (.XLSX)", 
                            data=buffer.getvalue(), 
                            file_name="resumen_reposicion_global.xlsx", 
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                            type="secondary",
                            use_container_width=True,
                            key="download_resumen_global"
                        )

                    # Descarga Completa (EXCEL)
                    with c_down2:
                        buffer_comp = io.BytesIO()
                        with pd.ExcelWriter(buffer_comp, engine='xlsxwriter') as writer:
                            df_display_final.to_excel(writer, index=False, sheet_name='Detalle')

                        st.download_button(
                            label="💾 DESCARGAR COMPLETA (.XLSX)", 
                            data=buffer_comp.getvalue(), 
                            file_name="resultado_reposicion_global.xlsx", 
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                            type="primary",
                            use_container_width=True,
                            key="download_repo_global"
                        )
                        
                # DEVOLUCIÓN
                else:
                    df_dev = st.session_state.data_calculada
                    
                    st.balloons()
                    st.markdown("### 📊 Tablero de Devoluciones y Excesos")
                    
                    # Alerta informativa dinámica
                    st.markdown(f"""
                    <div class="alert-info alert-box">
                        <strong>Criterio:</strong> Se consideran sobrantes aquellos productos con una cobertura mayor a <b>{umbral_devolucion}</b> (aprox {umbral_devolucion*12:.1f} meses).
                        La cantidad sugerida a devolver es el exceso por encima de ese umbral.
                    </div>
                    """, unsafe_allow_html=True)
                    
                    sucursales_view = ['BA', 'MDZ', 'SLT']
                    tabs = st.tabs([f"📍 {s}" for s in sucursales_view])
                    
                    for i, suc in enumerate(sucursales_view):
                        with tabs[i]:
                            # Corrección de clave en minúscula para coincidir con logic.py
                            col_exc_qty = f'excedente_qty_{suc.lower()}'
                            col_exc_peso = f'excedente_peso_{suc.lower()}'
                            col_exc_vol = f'excedente_vol_{suc.lower()}'
                            col_prioridad = f'prioridad_retorno_{suc.lower()}'
                            
                            # Filtramos solo lo que tiene excedente > 0
                            df_suc_dev = df_dev[df_dev[col_exc_qty] > 0].copy()
                            
                            if len(df_suc_dev) == 0:
                                st.success(f"✅ La sucursal {suc} no presenta excedentes significativos (> {umbral_devolucion} cobertura).")
                            else:
                                # KPIs Generales
                                c1, c2, c3, c4 = st.columns(4)
                                total_items = df_suc_dev['codigo'].nunique()
                                total_unidades = df_suc_dev[col_exc_qty].sum()
                                total_peso = df_suc_dev[col_exc_peso].sum()
                                total_vol = df_suc_dev[col_exc_vol].sum()
                                
                                # KPI Especial: Oportunidad de Retorno
                                # Cantidad de items que sobran acá y faltan en SF
                                items_match = df_suc_dev[df_suc_dev[col_prioridad]].shape[0]
                                kg_match = df_suc_dev[df_suc_dev[col_prioridad]][col_exc_peso].sum()

                                c1.metric("Items con Exceso", f"{total_items}")
                                c2.metric("Unidades Sobrantes", f"{total_unidades:,.0f}")
                                c3.metric("Peso Sobrante", f"{total_peso:,.0f} kg")
                                c4.metric("Volumen Sobrante", f"{total_vol:,.2f} m³")
                                
                                st.write("")
                                if items_match > 0:
                                    st.markdown(f"""
                                    <div class="alert-warning alert-box">
                                        🔥 <strong>Oportunidad de Retorno:</strong> Hay <b>{items_match} productos</b> ({kg_match:,.0f} kg) que sobran en {suc} 
                                        y actualmente <b>tienen déficit en Santa Fe</b>. Priorizar su carga.
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Tabla Resumen por Familia
                                st.markdown("##### 📦 Detalle por Familia")
                                df_grp = df_suc_dev.groupby('familia_logica').agg({
                                    col_exc_qty: 'sum',
                                    col_exc_peso: 'sum',
                                    col_exc_vol: 'sum',
                                    col_prioridad: 'sum' # Cuenta cuantos items son prioritarios
                                }).reset_index()
                                
                                df_grp.columns = ['Familia', 'Unidades Exceso', 'Peso (kg)', 'Volumen (m³)', 'Items Prioritarios (SF)']
                                st.dataframe(df_grp.style.format({
                                    'Unidades Exceso': '{:,.0f}',
                                    'Peso (kg)': '{:,.2f}',
                                    'Volumen (m³)': '{:,.2f}',
                                    'Items Prioritarios (SF)': '{:,.0f}'
                                }).background_gradient(subset=['Items Prioritarios (SF)'], cmap='Reds'), use_container_width=True)
                                
                                # Expander con detalle SKU
                                with st.expander(f"Ver detalle SKU de {suc}"):
                                    cols_detalle = ['familia_logica', 'codigo', 'descripcion', f'stock_{suc.lower()}', f'demanda_estimada_{suc.lower()}', col_exc_qty, col_prioridad]
                                    df_show_sku = df_suc_dev[cols_detalle].rename(columns={
                                        f'stock_{suc.lower()}': 'Stock Actual',
                                        f'demanda_estimada_{suc.lower()}': 'Demanda',
                                        col_exc_qty: 'Excedente Sugerido',
                                        col_prioridad: 'Sirve a SF?'
                                    })
                                    st.dataframe(df_show_sku, use_container_width=True)

                    # Descarga Global de Devoluciones (EXCEL)
                    st.divider()
                    st.markdown("### 📥 Descargas Globales")
                    buffer_dev = io.BytesIO()
                    with pd.ExcelWriter(buffer_dev, engine='xlsxwriter') as writer:
                        df_dev.to_excel(writer, index=False, sheet_name='Excedentes')

                    st.download_button(
                        "💾 Descargar Reporte de Excedentes (.XLSX)",
                        buffer_dev.getvalue(),
                        "analisis_devoluciones_global.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        key="download_dev_global"
                    )

    else:
        st.error("Error crítico al leer el archivo.")