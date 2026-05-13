import streamlit as st
import pandas as pd
import logic
import utils
import io
import os

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
if 'show_docs' not in st.session_state:
    st.session_state.show_docs = False


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN: Mostrar documentación en el área principal
# ─────────────────────────────────────────────────────────────────────────────
def mostrar_documentacion():
    """
    Lee y renderiza el archivo documentacion_reposicion.md en el área principal.
    También ofrece descarga del Word (.docx) si está disponible.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    doc_md_path   = os.path.join(base_dir, "documentacion_reposicion.md")
    doc_docx_path = os.path.join(base_dir, "documentacion_reposicion.docx")

    col_title, col_back = st.columns([5, 1])
    with col_title:
        st.title("📖 Manual de Usuario")
        st.caption("Documentación interna — Módulo de Reposición y Devoluciones")
    with col_back:
        st.write("")
        st.write("")
        if st.button("← Volver a la app", use_container_width=True):
            st.session_state.show_docs = False
            st.rerun()

    st.divider()

    # Botón de descarga Word
    if os.path.exists(doc_docx_path):
        with open(doc_docx_path, "rb") as f:
            st.download_button(
                label="📄 Descargar Manual en Word (.DOCX)",
                data=f.read(),
                file_name="Manual_Gestion_Stock_Sucursales.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="secondary"
            )
        st.write("")

    # Renderizar Markdown
    if os.path.exists(doc_md_path):
        with open(doc_md_path, "r", encoding="utf-8") as f:
            contenido = f.read()
        st.markdown(contenido)
    else:
        st.error(
            f"No se encontró el archivo de documentación.\n\n"
            f"Ruta esperada: `{doc_md_path}`\n\n"
            "Asegurate de que **documentacion_reposicion.md** esté en la misma carpeta que app.py."
        )


# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4143/4143163.png", width=60)
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
        ignorar_dns = st.checkbox("Ignorar Inmovilizado/A Demanda", value=True, help="Excluye items con Grupo Stock 'DNS - A Demanda' o 'DNS - Inmovilizado'")

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
        st.subheader("📍 Sucursal Origen")
        sucursal_origen = st.selectbox(
            "Seleccione Origen:",
            ["SF", "BA", "MDZ", "SLT"],
            index=0,
            help="Sucursal desde donde se enviará el stock"
        )

        st.subheader("📊 Lógica de Demanda")
        metodo_demanda = st.radio(
            "Método Estimación:",
            ('A', 'B'),
            index=1,
            horizontal=True,
            help="**Método A (Teórico):** Basado en parque de máquinas (Population) y coeficientes de familia.\n\n**Método B (Histórico):** Basado en histórico de ventas/reemplazos reciente (Recomendado)."
        )

        st.subheader("🎯 Coberturas (En meses)")
        cob_origen_meses = st.number_input(
            f"Cobertura Objetivo {sucursal_origen}",
            value=6.0,
            step=0.5,
            min_value=0.0,
            help="Cobertura en meses que debe mantener la sucursal origen"
        )
        cob_destino_meses = st.number_input(
            "Cobertura Objetivo Destinos",
            value=4.0,
            step=0.5,
            min_value=0.0,
            help="Cobertura en meses para todas las sucursales destino"
        )
        
    else:
        # Parametros modo Devolución
        st.subheader("📊 Parámetros Devolución")
        metodo_demanda = st.radio(
            "Método Estimación (Base):", 
            ('A', 'B'), 
            index=1,
            horizontal=True,
            help="**Método A:** Cálculo Teórico (Parque).\n**Método B:** Cálculo Histórico (Rotación)."
        )
        
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

    # ─── BOTÓN DE DOCUMENTACIÓN (al final del sidebar) ───────────────────────
    st.divider()
    if st.button("📖 Manual de Usuario", use_container_width=True, help="Ver la documentación completa del sistema"):
        st.session_state.show_docs = True
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ÁREA PRINCIPAL: si show_docs está activo, mostrar documentación y detener
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.show_docs:
    mostrar_documentacion()
    st.stop()


# --- ÁREA PRINCIPAL (normal) ---

col_header_1, col_header_2 = st.columns([3, 1])
with col_header_1:
    if modo_analisis == "Reposición (Envío)":
        if 'sucursal_origen' in locals():
            st.title(f"📦 Reposiciones: {sucursal_origen} ➔ Red")
            st.markdown(f"Cálculo de envíos desde {sucursal_origen} para abastecer la red.")
        else:
            st.title("📦 Reposiciones: Configurar Origen")
            st.markdown("Seleccione la sucursal origen en el panel lateral.")
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
            # APLICACION DE FILTROS (Incluyendo DNS)
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
                            st.session_state.data_calculada = None
                        else:
                            df_proc = logic.estimar_demanda(df_proc, metodo_demanda)
                            
                            # ----------------------------------------------------
                            #                 MODO REPOSICIÓN
                            # ----------------------------------------------------
                            if modo_analisis == "Reposición (Envío)":
                                df_proc = logic.calcular_coberturas(
                                    df_proc,
                                    sucursal_origen=sucursal_origen.lower(),
                                    cob_origen_meses=cob_origen_meses,
                                    cob_destino_meses=cob_destino_meses
                                )
                                df_final = logic.distribuir_stock(df_proc, sucursal_origen=sucursal_origen.lower())

                                # Determinar sucursales destino para cálculos
                                todas_sucursales = ['SF', 'BA', 'MDZ', 'SLT']
                                sucursales_destino_view = [s for s in todas_sucursales if s != sucursal_origen.upper()]

                                # Asegurar que existan columnas de tránsito
                                for col in ['qty_sf', 'qty_ba', 'qty_mdz', 'qty_slt',
                                           'qty_ot_transito_sf', 'qty_ot_transito_ba',
                                           'qty_ot_transito_mdz', 'qty_ot_transito_slt']:
                                    if col not in df_final.columns:
                                        df_final[col] = 0

                                # --- CÁLCULO DE COBERTURAS FINALES (Post Envío) - DINÁMICO ---
                                for suc in [s.lower() for s in sucursales_destino_view]:
                                    if suc == 'sf':
                                        col_stock = 'stock_total_sf_fisico'
                                        col_transito = 'qty_ot_transito_sf'
                                    else:
                                        col_stock = f'stock_{suc}'
                                        col_transito = f'qty_ot_transito_{suc}'

                                    col_envio = f'final_enviar_{suc}'
                                    col_demanda = f'demanda_estimada_{suc}'

                                    if col_stock in df_final.columns and col_envio in df_final.columns:
                                        stock_final = df_final[col_stock] + df_final.get(col_transito, 0) + df_final[col_envio]
                                        df_final[f'cobertura_fin_{suc}'] = stock_final / df_final[col_demanda].replace(0, 0.0001)

                                # --- LIMPIEZA DE DECIMALES ---
                                for col in df_final.columns:
                                    condicion_enteros = any(x in col for x in ['qty', 'qpres', 'qrem', 'stock', 'final_enviar', 'transito'])
                                    no_es_peso_vol = 'peso' not in col and 'volumen' not in col and 'cobertura' not in col
                                    
                                    if pd.api.types.is_numeric_dtype(df_final[col]):
                                        if condicion_enteros and no_es_peso_vol:
                                            df_final[col] = df_final[col].fillna(0).round(0).astype(int)
                                        elif 'diff' in col:
                                            df_final[col] = df_final[col].fillna(0).round(2)

                                # GUARDAR EN SESSION STATE
                                st.session_state.data_calculada = df_final
                                st.session_state.modo_calculado = "Reposición (Envío)"

                            # ----------------------------------------------------
                            #                 MODO DEVOLUCIÓN
                            # ----------------------------------------------------
                            else:
                                cols_sf_fisico = ['stock_sf', 'stock_aux', 'stock_sv_arg', 'stock_sv_min', 'stock_ns_noa']
                                for c in cols_sf_fisico: 
                                    if c not in df_proc.columns: df_proc[c] = 0
                                df_proc['stock_total_sf_fisico'] = df_proc[cols_sf_fisico].sum(axis=1)

                                df_dev = logic.calcular_excedentes_sucursales(df_proc, umbral_meses_exceso=umbral_devolucion)
                                
                                st.session_state.data_calculada = df_dev
                                st.session_state.modo_calculado = "Devolución (Sobrantes)"


            # --- VISUALIZACIÓN (SE EJECUTA SI HAY DATOS EN SESIÓN) ---
            if st.session_state.data_calculada is not None and st.session_state.modo_calculado == modo_analisis:
                
                # REPOSICIÓN
                if modo_analisis == "Reposición (Envío)":
                    df_final = st.session_state.data_calculada

                    # --- DETERMINAR SUCURSALES DESTINO DINÁMICAMENTE ---
                    todas_sucursales = ['SF', 'BA', 'MDZ', 'SLT']
                    sucursales_destino_view = [s for s in todas_sucursales if s != sucursal_origen.upper()]

                    # --- PREPARACIÓN DE DATOS PARA VISTA PRINCIPAL ---
                    column_map = {
                        'familia_logica': 'Familia Logica',
                        'familia': 'Familia',
                        'subfamilia': 'Subfamilia',
                        'subfamilia2': 'Subfamilia2',
                        'grupo_stock': 'Grupo Stock',
                        'codigo': 'Codigo',
                        'descripcion': 'Descripcion',
                        'datos_y_aplicaciones': 'Datos y aplicaciones',
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
                        'qty_sf': 'Transito EE SF',
                        'qty_ot_transito_sf': 'Transito OT SF',
                        'cobertura_ini_sf': 'cobertura inicial SF',
                        'cobertura_ampliada_sf': 'Cobertura Ampliada SF',
                        'diff_sf': 'Sobra/Falta SF',
                        # BA
                        'qpresba': 'QPresBA',
                        'qremba': 'QRemBA',
                        'demanda_estimada_ba': 'D.EST BA',
                        'stock_ba': 'Stock BA',
                        'qty_ot_transito_ba': 'Transito OT BA',
                        'qty_ba': 'Envío Entrante BA',
                        'cobertura_ini_ba': 'cobertura inicial BA',
                        'cobertura_ampliada_ba': 'Cobertura Ampliada BA',
                        'diff_ba': 'Sobra / Falta BA',
                        'final_enviar_ba': 'q enviar BA',
                        # MDZ
                        'qpresmdz': 'QPresMDZ',
                        'qremmdz': 'QRemMDZ',
                        'demanda_estimada_mdz': 'D.EST MDZ',
                        'stock_mdz': 'Stock MDZ',
                        'qty_ot_transito_mdz': 'Transito OT MDZ',
                        'qty_mdz': 'Envío Entrante MDZ',
                        'cobertura_ini_mdz': 'cobertura inicial MDZ',
                        'cobertura_ampliada_mdz': 'Cobertura Ampliada MDZ',
                        'diff_mdz': 'Sobra / Falta MDZ',
                        'final_enviar_mdz': 'q enviar MDZ',
                        # SLT
                        'qpresslt': 'QPresSLT',
                        'qremslt': 'QRemSLT',
                        'demanda_estimada_slt': 'D.EST SLT',
                        'stock_slt': 'Stock SLT',
                        'qty_ot_transito_slt': 'Transito OT SLT',
                        'qty_slt': 'Envío Entrante SLT',
                        'cobertura_ini_slt': 'cobertura inicial SLT',
                        'cobertura_ampliada_slt': 'Cobertura Ampliada SLT',
                        'diff_slt': 'Sobra / Falta SLT',
                        'final_enviar_slt': 'q enviar SLT',
                        # SF (cuando es destino)
                        'final_enviar_sf': 'q enviar SF',
                        'cobertura_fin_sf': 'Cob. Fin SF'
                    }
                    
                    final_order = [
                        'Familia Logica', 'Familia', 'Subfamilia', 'Subfamilia2', 'Grupo Stock', 'Codigo', 'Descripcion', 'Datos y aplicaciones',
                        'qty piezas', 'peso', 'volumen', 'q pres total', 'q rem total', 'Wproducto', 'Wfamilia', 'd est total',
                        'stock total', 'cobertura total',
                        'q pres SF', 'Q rem SF', 'D est SF',
                        'Stock SF', 'Stock Aux', 'Stock SV ARG', 'Stock SV MIN', 'Stock NS NOA',
                        'Transito EE SF', 'Transito OT SF',
                        'Stock SF Final',
                        'cobertura inicial SF', 'Cobertura Ampliada SF',
                        'Sobra/Falta SF', 'q enviar SF',
                        'QPresBA', 'QRemBA', 'D.EST BA', 'Stock BA', 'Transito OT BA', 'Envío Entrante BA',
                        'cobertura inicial BA', 'Cobertura Ampliada BA', 'Sobra / Falta BA', 'q enviar BA',
                        'QPresMDZ', 'QRemMDZ', 'D.EST MDZ', 'Stock MDZ', 'Transito OT MDZ', 'Envío Entrante MDZ',
                        'cobertura inicial MDZ', 'Cobertura Ampliada MDZ', 'Sobra / Falta MDZ', 'q enviar MDZ',
                        'QPresSLT', 'QRemSLT', 'D.EST SLT', 'Stock SLT', 'Transito OT SLT', 'Envío Entrante SLT',
                        'cobertura inicial SLT', 'Cobertura Ampliada SLT', 'Sobra / Falta SLT', 'q enviar SLT'
                    ]
                    
                    # Relleno de columnas faltantes visuales
                    for col_internal, col_final in column_map.items():
                        if col_internal not in df_final.columns:
                            df_final[col_internal] = 0 

                    df_view = df_final.rename(columns=column_map)
                    cols_existentes = [c for c in final_order if c in df_view.columns]
                    df_view = df_view[cols_existentes]
                    
                    # --- NUEVA PLANILLA RESUMEN ---
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
                        'stock_total_sf_fisico': 'Stock SF Físico',
                        'qty_sf': 'Envío Entrante SF',
                        'qty_ot_transito_sf': 'Tránsito OT SF',
                        'cobertura_ini_sf': 'Cob. Ini SF',
                        'cobertura_ampliada_sf': 'Cob. Ampliada SF',
                        'diff_sf': 'Sobra / Falta SF',
                        'final_enviar_sf': 'Cant. Enviar SF',
                        'cobertura_fin_sf': 'Cob. Fin SF',
                        # BA
                        'qpresba': 'QPresBA',
                        'qremba': 'QRemBA',
                        'demanda_estimada_ba': 'D.EST BA',
                        'stock_ba': 'Stock BA',
                        'qty_ot_transito_ba': 'Tránsito OT BA',
                        'qty_ba': 'Envío Entrante BA',
                        'cobertura_ini_ba': 'Cob. Ini BA',
                        'cobertura_ampliada_ba': 'Cob. Ampliada BA',
                        'diff_ba': 'Sobra / Falta BA',
                        'final_enviar_ba': 'Cant. Enviar BA',
                        'cobertura_fin_ba': 'Cob. Fin BA',
                        # MDZ
                        'qpresmdz': 'QPresMDZ',
                        'qremmdz': 'QRemMDZ',
                        'demanda_estimada_mdz': 'D.EST MDZ',
                        'stock_mdz': 'Stock MDZ',
                        'qty_ot_transito_mdz': 'Tránsito OT MDZ',
                        'qty_mdz': 'Envío Entrante MDZ',
                        'cobertura_ini_mdz': 'Cob. Ini MDZ',
                        'cobertura_ampliada_mdz': 'Cob. Ampliada MDZ',
                        'diff_mdz': 'Sobra / Falta MDZ',
                        'final_enviar_mdz': 'Cant. Enviar MDZ',
                        'cobertura_fin_mdz': 'Cob. Fin MDZ',
                        # SLT
                        'qpresslt': 'QPresSLT',
                        'qremslt': 'QRemSLT',
                        'demanda_estimada_slt': 'D.EST SALTA',
                        'stock_slt': 'Stock SLT',
                        'qty_slt': 'Envío Entrante SLT',
                        'qty_ot_transito_slt': 'Tránsito OT SLT',
                        'cobertura_ini_slt': 'Cob. Ini SLT',
                        'cobertura_ampliada_slt': 'Cob. Ampliada SLT',
                        'diff_slt': 'Sobra / Falta SLT',
                        'final_enviar_slt': 'Cant. Enviar SLT',
                        'cobertura_fin_slt': 'Cob. Fin SLT'
                    }
                    
                    # Extraer datos para resumen usando df_final original
                    df_resumen = pd.DataFrame()
                    for col_orig, col_dest in cols_resumen_map.items():
                        if col_orig in df_final.columns:
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
                    
                    # Pre-cálculo de columnas de totales para resumen (dinámico)
                    for suc in sucursales_destino_view:
                        col_envio = f'q enviar {suc}'
                        if col_envio not in df_view.columns:
                            continue

                        df_view[f'peso_total_{suc}'] = df_view[col_envio] * df_view['peso']
                        df_view[f'vol_total_{suc}'] = df_view[col_envio] * df_view['volumen']

                        col_demanda_orig = f'demanda_estimada_{suc.lower()}'
                        if suc.upper() == 'SF':
                            col_stock_orig = 'stock_total_sf_fisico'
                            col_transito_orig = 'qty_ot_transito_sf'
                        else:
                            col_stock_orig = f'stock_{suc.lower()}'
                            col_transito_orig = f'qty_ot_transito_{suc.lower()}'
                        col_enviar_orig = f'final_enviar_{suc.lower()}'

                        if col_stock_orig in df_final.columns and col_demanda_orig in df_final.columns:
                            stock_actual = df_final[col_stock_orig] + df_final.get(col_transito_orig, 0)
                            demanda = df_final[col_demanda_orig]

                            cob_antes = stock_actual / demanda.replace(0, 0.00001)
                            cob_despues = (stock_actual + df_final.get(col_enviar_orig, 0)) / demanda.replace(0, 0.00001)

                            df_view[f'risk_antes_{suc}'] = cob_antes < 0.0833
                            df_view[f'salvados_{suc}'] = (df_view[f'risk_antes_{suc}']) & (cob_despues >= 0.0833)

                    # PREPARAR DATA PARA DESCARGA (Limpieza de columnas visuales)
                    cols_mostrar = [c for c in df_view.columns if 'risk_' not in c and 'salvados_' not in c and 'peso_total' not in c and 'vol_total' not in c]
                    df_display_final = df_view[cols_mostrar]

                    # --- TABS DE SUCURSALES (DINÁMICO SEGÚN ORIGEN) ---
                    tabs = st.tabs([f"📍 {s}" for s in sucursales_destino_view])

                    for i, suc in enumerate(sucursales_destino_view):
                        with tabs[i]:
                            col_envio = f'q enviar {suc}'
                            if col_envio not in df_view.columns:
                                st.warning(f"No hay datos de envío para {suc}")
                                continue
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
                            
                            st.write("")
                            
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
                                
                                cols_total = ['q pres total', 'q rem total', 'Wproducto', 'Wfamilia', 'd est total', 'stock total', 'cobertura total']
                                cols_sf = [c for c in df_display_final.columns if 'SF' in c or c in ['Stock Aux', 'Stock SV ARG', 'Stock SV MIN', 'Stock NS NOA']]
                                cols_ba = [c for c in df_display_final.columns if 'BA' in c]
                                cols_mdz = [c for c in df_display_final.columns if 'MDZ' in c]
                                cols_slt = [c for c in df_display_final.columns if 'SLT' in c]
                                
                                cols_total = [c for c in cols_total if c in df_display_final.columns]
                                cols_sf = [c for c in cols_sf if c in df_display_final.columns]

                                format_dict = {c: "{:.2f}" for c in df_display_final.select_dtypes(include='float').columns}

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
                    
                    # Descarga Resumen (EXCEL CON FORMATO)
                    with c_down1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_resumen.to_excel(writer, index=False, sheet_name='Resumen')

                            workbook = writer.book
                            worksheet = writer.sheets['Resumen']

                            fmt_rango1 = workbook.add_format({'bg_color': '#E8F4F8'})
                            fmt_rango1_last = workbook.add_format({'bg_color': '#C8E4F0'})
                            fmt_rango2 = workbook.add_format({'bg_color': '#F0F8E8'})
                            fmt_rango2_last = workbook.add_format({'bg_color': '#D8F0C8'})
                            fmt_rango3 = workbook.add_format({'bg_color': '#FFF4E6'})
                            fmt_rango3_last = workbook.add_format({'bg_color': '#FFE8C8'})
                            fmt_rango4 = workbook.add_format({'bg_color': '#F8E8F4'})
                            fmt_rango4_last = workbook.add_format({'bg_color': '#F0D0E8'})
                            fmt_rango5 = workbook.add_format({'bg_color': '#E8F8F0'})
                            fmt_rango5_last = workbook.add_format({'bg_color': '#D0F0E0'})

                            for col in range(0, min(17, len(df_resumen.columns))):
                                worksheet.set_column(col, col, None, fmt_rango1)
                            if len(df_resumen.columns) > 17:
                                worksheet.set_column(17, 17, None, fmt_rango1_last)

                            for col in range(18, min(32, len(df_resumen.columns))):
                                worksheet.set_column(col, col, None, fmt_rango2)
                            if len(df_resumen.columns) > 32:
                                worksheet.set_column(32, 32, None, fmt_rango2_last)

                            for col in range(33, min(42, len(df_resumen.columns))):
                                worksheet.set_column(col, col, None, fmt_rango3)
                            if len(df_resumen.columns) > 42:
                                worksheet.set_column(42, 42, None, fmt_rango3_last)

                            for col in range(43, min(52, len(df_resumen.columns))):
                                worksheet.set_column(col, col, None, fmt_rango4)
                            if len(df_resumen.columns) > 52:
                                worksheet.set_column(52, 52, None, fmt_rango4_last)

                            for col in range(53, min(62, len(df_resumen.columns))):
                                worksheet.set_column(col, col, None, fmt_rango5)
                            if len(df_resumen.columns) > 62:
                                worksheet.set_column(62, 62, None, fmt_rango5_last)

                        st.download_button(
                            label="📋 DESCARGAR RESUMEN (.XLSX)",
                            data=buffer.getvalue(),
                            file_name="resumen_reposicion_global.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="secondary",
                            use_container_width=True,
                            key="download_resumen_global"
                        )

                    # Descarga Completa (EXCEL CON FORMATO)
                    with c_down2:
                        buffer_comp = io.BytesIO()
                        with pd.ExcelWriter(buffer_comp, engine='xlsxwriter') as writer:
                            df_display_final.to_excel(writer, index=False, sheet_name='Detalle')

                            workbook = writer.book
                            worksheet = writer.sheets['Detalle']

                            fmt_rango1 = workbook.add_format({'bg_color': '#E8F4F8'})
                            fmt_rango1_last = workbook.add_format({'bg_color': '#C8E4F0'})
                            fmt_rango2 = workbook.add_format({'bg_color': '#F0F8E8'})
                            fmt_rango2_last = workbook.add_format({'bg_color': '#D8F0C8'})
                            fmt_rango3 = workbook.add_format({'bg_color': '#FFF4E6'})
                            fmt_rango3_last = workbook.add_format({'bg_color': '#FFE8C8'})
                            fmt_rango4 = workbook.add_format({'bg_color': '#F8E8F4'})
                            fmt_rango4_last = workbook.add_format({'bg_color': '#F0D0E8'})
                            fmt_rango5 = workbook.add_format({'bg_color': '#E8F8F0'})
                            fmt_rango5_last = workbook.add_format({'bg_color': '#D0F0E0'})

                            for col in range(0, min(17, len(df_display_final.columns))):
                                worksheet.set_column(col, col, None, fmt_rango1)
                            if len(df_display_final.columns) > 17:
                                worksheet.set_column(17, 17, None, fmt_rango1_last)

                            for col in range(18, min(32, len(df_display_final.columns))):
                                worksheet.set_column(col, col, None, fmt_rango2)
                            if len(df_display_final.columns) > 32:
                                worksheet.set_column(32, 32, None, fmt_rango2_last)

                            for col in range(33, min(42, len(df_display_final.columns))):
                                worksheet.set_column(col, col, None, fmt_rango3)
                            if len(df_display_final.columns) > 42:
                                worksheet.set_column(42, 42, None, fmt_rango3_last)

                            for col in range(43, min(52, len(df_display_final.columns))):
                                worksheet.set_column(col, col, None, fmt_rango4)
                            if len(df_display_final.columns) > 52:
                                worksheet.set_column(52, 52, None, fmt_rango4_last)

                            for col in range(53, min(62, len(df_display_final.columns))):
                                worksheet.set_column(col, col, None, fmt_rango5)
                            if len(df_display_final.columns) > 62:
                                worksheet.set_column(62, 62, None, fmt_rango5_last)

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
                            col_exc_qty = f'excedente_qty_{suc.lower()}'
                            col_exc_peso = f'excedente_peso_{suc.lower()}'
                            col_exc_vol = f'excedente_vol_{suc.lower()}'
                            col_prioridad = f'prioridad_retorno_{suc.lower()}'
                            
                            df_suc_dev = df_dev[df_dev[col_exc_qty] > 0].copy()
                            
                            if len(df_suc_dev) == 0:
                                st.success(f"✅ La sucursal {suc} no presenta excedentes significativos (> {umbral_devolucion} cobertura).")
                            else:
                                c1, c2, c3, c4 = st.columns(4)
                                total_items = df_suc_dev['codigo'].nunique()
                                total_unidades = df_suc_dev[col_exc_qty].sum()
                                total_peso = df_suc_dev[col_exc_peso].sum()
                                total_vol = df_suc_dev[col_exc_vol].sum()
                                
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
                                
                                st.markdown("##### 📦 Detalle por Familia")
                                df_grp = df_suc_dev.groupby('familia_logica').agg({
                                    col_exc_qty: 'sum',
                                    col_exc_peso: 'sum',
                                    col_exc_vol: 'sum',
                                    col_prioridad: 'sum'
                                }).reset_index()
                                
                                df_grp.columns = ['Familia', 'Unidades Exceso', 'Peso (kg)', 'Volumen (m³)', 'Items Prioritarios (SF)']

                                def _reds_gradient(col):
                                    vmax = col.max()
                                    if pd.isna(vmax) or vmax <= 0:
                                        return ['' for _ in col]
                                    styles = []
                                    for v in col:
                                        try:
                                            ratio = float(v) / float(vmax)
                                        except (TypeError, ValueError):
                                            ratio = 0
                                        ratio = max(0.0, min(1.0, ratio))
                                        r = 255
                                        g = int(245 - 165 * ratio)
                                        b = int(240 - 200 * ratio)
                                        text = '#ffffff' if ratio > 0.6 else '#000000'
                                        styles.append(f'background-color: rgb({r},{g},{b}); color: {text}')
                                    return styles

                                st.dataframe(df_grp.style.format({
                                    'Unidades Exceso': '{:,.0f}',
                                    'Peso (kg)': '{:,.2f}',
                                    'Volumen (m³)': '{:,.2f}',
                                    'Items Prioritarios (SF)': '{:,.0f}'
                                }).apply(_reds_gradient, subset=['Items Prioritarios (SF)']), use_container_width=True)
                                
                                with st.expander(f"Ver detalle SKU de {suc}"):
                                    cols_detalle = ['familia_logica', 'codigo', 'descripcion', f'stock_{suc.lower()}', f'demanda_estimada_{suc.lower()}', col_exc_qty, col_prioridad]
                                    df_show_sku = df_suc_dev[cols_detalle].rename(columns={
                                        f'stock_{suc.lower()}': 'Stock Actual',
                                        f'demanda_estimada_{suc.lower()}': 'Demanda',
                                        col_exc_qty: 'Excedente Sugerido',
                                        col_prioridad: 'Sirve a SF?'
                                    })
                                    st.dataframe(df_show_sku, use_container_width=True)

                    # Descarga Global de Devoluciones (EXCEL CON FORMATO)
                    st.divider()
                    st.markdown("### 📥 Descargas Globales")

                    df_export = df_dev.copy()

                    suc_codes = ['ba', 'mdz', 'slt']
                    suc_labels = {'ba': 'BA', 'mdz': 'MDZ', 'slt': 'SLT'}

                    # Aseguramos columnas auxiliares
                    for suc in suc_codes:
                        for c in [f'excedente_qty_{suc}', f'excedente_peso_{suc}', f'excedente_vol_{suc}', f'prioridad_retorno_{suc}']:
                            if c not in df_export.columns:
                                df_export[c] = 0

                    # Columnas derivadas: totales y recomendación
                    df_export['total_excedente_qty'] = sum(df_export[f'excedente_qty_{s}'] for s in suc_codes)
                    df_export['total_excedente_peso'] = sum(df_export[f'excedente_peso_{s}'] for s in suc_codes)
                    df_export['total_excedente_vol'] = sum(df_export[f'excedente_vol_{s}'] for s in suc_codes)

                    def _sucursales_prioritarias(row):
                        marcadas = [suc_labels[s] for s in suc_codes if bool(row.get(f'prioridad_retorno_{s}', False))]
                        return ' + '.join(marcadas) if marcadas else ''

                    def _sucursales_con_excedente(row):
                        marcadas = [suc_labels[s] for s in suc_codes if float(row.get(f'excedente_qty_{s}', 0) or 0) > 0]
                        return ' + '.join(marcadas) if marcadas else ''

                    df_export['sucursales_prioritarias'] = df_export.apply(_sucursales_prioritarias, axis=1)
                    df_export['sucursales_con_excedente'] = df_export.apply(_sucursales_con_excedente, axis=1)

                    def _recomendacion(row):
                        if row['sucursales_prioritarias']:
                            return '✅ DEVOLVER A SF'
                        if row['total_excedente_qty'] > 0:
                            return '⚠️ Excedente sin demanda en SF'
                        return '— Sin excedente'

                    df_export['recomendacion'] = df_export.apply(_recomendacion, axis=1)

                    # Orden de columnas explícito por bloques
                    col_identificacion = [c for c in ['codigo', 'descripcion', 'familia_logica', 'familia', 'subfamilia', 'subfamilia2', 'grupo_stock', 'peso', 'volumen'] if c in df_export.columns]
                    col_recomendacion = ['recomendacion', 'sucursales_prioritarias', 'sucursales_con_excedente', 'total_excedente_qty', 'total_excedente_peso', 'total_excedente_vol']
                    col_sf = [c for c in ['stock_total_sf_fisico', 'demanda_estimada_sf', 'sf_deficit', 'sf_necesita_stock'] if c in df_export.columns]

                    col_por_suc = {}
                    for suc in suc_codes:
                        col_transito = 'qty_ot_transito_slt' if suc == 'slt' else f'qty_transito_{suc}'
                        col_por_suc[suc] = [c for c in [
                            f'stock_{suc}', col_transito, f'demanda_estimada_{suc}',
                            f'excedente_qty_{suc}', f'excedente_peso_{suc}', f'excedente_vol_{suc}',
                            f'prioridad_retorno_{suc}'
                        ] if c in df_export.columns]

                    columnas_ordenadas = col_identificacion + col_recomendacion + col_sf + col_por_suc['ba'] + col_por_suc['mdz'] + col_por_suc['slt']
                    columnas_ordenadas = [c for c in columnas_ordenadas if c in df_export.columns]
                    df_export = df_export[columnas_ordenadas]

                    # Ordenar filas: primero las prioritarias, luego excedente total descendente
                    df_export = df_export.assign(
                        _orden_reco=df_export['recomendacion'].map({'✅ DEVOLVER A SF': 0, '⚠️ Excedente sin demanda en SF': 1, '— Sin excedente': 2})
                    ).sort_values(by=['_orden_reco', 'total_excedente_peso'], ascending=[True, False]).drop(columns=['_orden_reco'])

                    # Headers en español más legibles
                    headers_legibles = {
                        'codigo': 'Código',
                        'descripcion': 'Descripción',
                        'familia_logica': 'Familia Lógica',
                        'familia': 'Familia',
                        'subfamilia': 'Subfamilia',
                        'subfamilia2': 'Subfamilia 2',
                        'grupo_stock': 'Grupo Stock',
                        'peso': 'Peso (kg/u)',
                        'volumen': 'Volumen (m³/u)',
                        'recomendacion': 'Recomendación',
                        'sucursales_prioritarias': 'Sucursales Prioritarias',
                        'sucursales_con_excedente': 'Sucursales c/ Excedente',
                        'total_excedente_qty': 'Excedente Total (u)',
                        'total_excedente_peso': 'Excedente Total (kg)',
                        'total_excedente_vol': 'Excedente Total (m³)',
                        'stock_total_sf_fisico': 'SF · Stock Físico',
                        'demanda_estimada_sf': 'SF · Demanda',
                        'sf_deficit': 'SF · Déficit',
                        'sf_necesita_stock': 'SF · ¿Necesita?',
                    }
                    for suc in suc_codes:
                        s_up = suc_labels[suc]
                        headers_legibles.update({
                            f'stock_{suc}': f'{s_up} · Stock',
                            f'qty_transito_{suc}': f'{s_up} · Tránsito',
                            'qty_ot_transito_slt': 'SLT · Tránsito',
                            f'demanda_estimada_{suc}': f'{s_up} · Demanda',
                            f'excedente_qty_{suc}': f'{s_up} · Excedente (u)',
                            f'excedente_peso_{suc}': f'{s_up} · Excedente (kg)',
                            f'excedente_vol_{suc}': f'{s_up} · Excedente (m³)',
                            f'prioridad_retorno_{suc}': f'{s_up} · Prioritario SF',
                        })

                    df_to_write = df_export.rename(columns=headers_legibles)

                    buffer_dev = io.BytesIO()
                    with pd.ExcelWriter(buffer_dev, engine='xlsxwriter') as writer:
                        df_to_write.to_excel(writer, index=False, sheet_name='Excedentes', startrow=1, header=False)

                        workbook = writer.book
                        worksheet = writer.sheets['Excedentes']

                        n_rows = len(df_to_write)
                        n_cols = len(df_to_write.columns)
                        last_row = n_rows  # cabecera está en fila 0 → datos van de 1 a n_rows

                        # Paleta por bloque (header oscuro, cuerpo claro)
                        palette = {
                            'id':   {'header': '#374151', 'body': '#F3F4F6'},  # gris
                            'reco': {'header': '#B45309', 'body': '#FFF7ED'},  # ámbar destacado
                            'sf':   {'header': '#1D4ED8', 'body': '#EFF6FF'},  # azul
                            'ba':   {'header': '#047857', 'body': '#ECFDF5'},  # verde
                            'mdz':  {'header': '#9D174D', 'body': '#FDF2F8'},  # rosa/magenta
                            'slt':  {'header': '#6D28D9', 'body': '#F5F3FF'},  # violeta
                        }

                        def _bloque_de(col_name):
                            if col_name in col_identificacion:
                                return 'id'
                            if col_name in col_recomendacion:
                                return 'reco'
                            if col_name in col_sf:
                                return 'sf'
                            for s in suc_codes:
                                if col_name in col_por_suc[s]:
                                    return s
                            return 'id'

                        # Formatos de header por bloque
                        header_fmts = {
                            k: workbook.add_format({
                                'bold': True, 'font_color': 'white', 'bg_color': v['header'],
                                'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
                                'border': 1, 'border_color': '#FFFFFF'
                            }) for k, v in palette.items()
                        }

                        # Formatos de cuerpo (numéricos + texto) por bloque
                        def _body_fmt(bloque, kind='int'):
                            base = {'bg_color': palette[bloque]['body'], 'valign': 'vcenter', 'border': 1, 'border_color': '#E5E7EB'}
                            if kind == 'int':
                                base['num_format'] = '#,##0'
                            elif kind == 'float2':
                                base['num_format'] = '#,##0.00'
                            elif kind == 'float3':
                                base['num_format'] = '#,##0.000'
                            elif kind == 'bool':
                                base['align'] = 'center'
                            elif kind == 'text':
                                base['align'] = 'left'
                            return workbook.add_format(base)

                        # Resolver tipo de columna para formato numérico
                        def _kind_of(col_internal):
                            if col_internal in ('peso',):
                                return 'float3'
                            if col_internal == 'volumen' or col_internal.startswith('excedente_vol_') or col_internal == 'total_excedente_vol':
                                return 'float3'
                            if col_internal.startswith('excedente_peso_') or col_internal == 'total_excedente_peso':
                                return 'float2'
                            if col_internal == 'sf_deficit':
                                return 'float2'
                            if col_internal in ('sf_necesita_stock',) or col_internal.startswith('prioridad_retorno_'):
                                return 'bool'
                            if col_internal.startswith('demanda_estimada_'):
                                return 'float2'
                            if col_internal in ('codigo', 'descripcion', 'familia_logica', 'familia', 'subfamilia', 'subfamilia2', 'grupo_stock', 'recomendacion', 'sucursales_prioritarias', 'sucursales_con_excedente'):
                                return 'text'
                            return 'int'

                        # Anchos sugeridos
                        widths = {
                            'codigo': 14, 'descripcion': 36, 'familia_logica': 14, 'familia': 16,
                            'subfamilia': 18, 'subfamilia2': 18, 'grupo_stock': 18,
                            'peso': 10, 'volumen': 12,
                            'recomendacion': 28, 'sucursales_prioritarias': 18, 'sucursales_con_excedente': 18,
                            'total_excedente_qty': 14, 'total_excedente_peso': 16, 'total_excedente_vol': 16,
                            'stock_total_sf_fisico': 14, 'demanda_estimada_sf': 14, 'sf_deficit': 14, 'sf_necesita_stock': 12,
                        }
                        for suc in suc_codes:
                            s_up = suc_labels[suc]
                            widths.update({
                                f'stock_{suc}': 10, f'qty_transito_{suc}': 12, 'qty_ot_transito_slt': 12,
                                f'demanda_estimada_{suc}': 12, f'excedente_qty_{suc}': 13,
                                f'excedente_peso_{suc}': 14, f'excedente_vol_{suc}': 14,
                                f'prioridad_retorno_{suc}': 12,
                            })

                        # Aplicar header + column format
                        for idx, col_internal in enumerate(columnas_ordenadas):
                            bloque = _bloque_de(col_internal)
                            kind = _kind_of(col_internal)
                            header_label = headers_legibles.get(col_internal, col_internal)
                            worksheet.write(0, idx, header_label, header_fmts[bloque])
                            worksheet.set_column(idx, idx, widths.get(col_internal, 12), _body_fmt(bloque, kind))

                        worksheet.set_row(0, 38)  # alto del header

                        # Freeze panes después de Código + Descripción
                        freeze_cols = min(2, n_cols)
                        worksheet.freeze_panes(1, freeze_cols)

                        # Autofiltro
                        if n_rows > 0:
                            worksheet.autofilter(0, 0, last_row, n_cols - 1)

                        # ───── Formato condicional ─────
                        if n_rows > 0:
                            # 1) Resaltar fila completa cuando Recomendación = "✅ DEVOLVER A SF"
                            reco_col_idx = columnas_ordenadas.index('recomendacion')
                            reco_letter = chr(ord('A') + reco_col_idx) if reco_col_idx < 26 else None
                            # xlsxwriter requiere referencia A1 — uso xl_col_to_name por seguridad
                            from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell
                            reco_cell_first = xl_rowcol_to_cell(1, reco_col_idx, row_abs=False, col_abs=True)

                            fmt_row_devolver = workbook.add_format({'bg_color': '#DCFCE7', 'bold': True})
                            fmt_row_warn = workbook.add_format({'bg_color': '#FEF3C7'})

                            worksheet.conditional_format(1, 0, last_row, n_cols - 1, {
                                'type': 'formula',
                                'criteria': f'=${xl_col_to_name(reco_col_idx)}2="✅ DEVOLVER A SF"',
                                'format': fmt_row_devolver
                            })
                            worksheet.conditional_format(1, 0, last_row, n_cols - 1, {
                                'type': 'formula',
                                'criteria': f'=${xl_col_to_name(reco_col_idx)}2="⚠️ Excedente sin demanda en SF"',
                                'format': fmt_row_warn
                            })

                            # 2) Escala de color sobre columnas de excedente (qty / peso) por sucursal y total
                            scale_cols = [
                                'total_excedente_qty', 'total_excedente_peso',
                                'excedente_qty_ba', 'excedente_peso_ba',
                                'excedente_qty_mdz', 'excedente_peso_mdz',
                                'excedente_qty_slt', 'excedente_peso_slt',
                            ]
                            for c in scale_cols:
                                if c in columnas_ordenadas:
                                    ci = columnas_ordenadas.index(c)
                                    worksheet.conditional_format(1, ci, last_row, ci, {
                                        'type': '3_color_scale',
                                        'min_color': '#FFFFFF',
                                        'mid_color': '#FDE68A',
                                        'max_color': '#DC2626'
                                    })

                            # 3) Resaltar SF · Déficit positivo (rojo) y negativo (verde claro)
                            if 'sf_deficit' in columnas_ordenadas:
                                ci = columnas_ordenadas.index('sf_deficit')
                                worksheet.conditional_format(1, ci, last_row, ci, {
                                    'type': 'cell', 'criteria': '>', 'value': 0,
                                    'format': workbook.add_format({'bg_color': '#FECACA', 'bold': True})
                                })

                            # 4) Booleanos prioridad/necesita: verde si TRUE
                            bool_cols = ['sf_necesita_stock'] + [f'prioridad_retorno_{s}' for s in suc_codes]
                            for c in bool_cols:
                                if c in columnas_ordenadas:
                                    ci = columnas_ordenadas.index(c)
                                    worksheet.conditional_format(1, ci, last_row, ci, {
                                        'type': 'text', 'criteria': 'containing', 'value': 'True',
                                        'format': workbook.add_format({'bg_color': '#A7F3D0', 'bold': True, 'align': 'center'})
                                    })

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
