# 📦 Manual de Usuario — Módulo de Reposición y Devoluciones

---

## 1. Introducción y Propósito

Esta herramienta centraliza el cálculo de cantidades a reponer en cada sucursal de la red (BA, MDZ, SLT) a partir del stock disponible en la sucursal de origen (habitualmente Santa Fe). Su objetivo es reemplazar el criterio manual y subjetivo por un proceso sistemático, reproducible y auditable que considera simultáneamente:

- La demanda histórica y/o presupuestada de cada producto en cada sucursal.
- El stock físico disponible en la sucursal origen (incluyendo depósitos auxiliares).
- El stock en tránsito (órdenes de traslado pendientes de llegar).
- Las coberturas objetivo definidas por el usuario para origen y destinos.
- Las reglas de empaque propias de cada familia de productos (cajas cerradas para filtros, juegos completos para rodaje y repuestos).

La herramienta opera en dos modos complementarios: **Reposición** (envío desde origen hacia sucursales) y **Devolución** (identificación de sobrantes en sucursales para retornar al origen).

---

## 2. Estructura General del Proceso

El cálculo de reposición sigue una cadena de pasos secuenciales. Cada paso alimenta al siguiente.

| Etapa | Qué hace |
|---|---|
| 1. Carga y filtrado de datos | Se lee el archivo CSV maestro y se excluyen ítems según los filtros configurados. |
| 2. Clasificación en familias lógicas | Cada producto se asigna a una familia (GET, RODAJE, DONALDSON, TURBO, KTN, REPUESTOS, OTROS). |
| 3. Cálculo de coeficientes W | Se calcula cuánto se vendió respecto a lo presupuestado, a nivel producto (Wp) y familia (Wf). |
| 4. Estimación de demanda | Se estima la demanda anual de cada producto en cada sucursal (Método A o B). |
| 5. Cálculo de coberturas y brechas | Se compara el stock disponible (físico + tránsito) contra el objetivo de cobertura para detectar faltantes o excedentes. |
| 6. Distribución de stock | Se calculan las cantidades a enviar a cada sucursal, respetando disponibilidad, empaque y prioridad por necesidad. |

---

## 3. Filtros de Datos

Antes de ejecutar cualquier cálculo, el sistema aplica filtros para depurar el universo de productos a analizar. Todos los filtros están activos por defecto y pueden habilitarse o deshabilitarse desde el panel lateral.

| Filtro | Activo por defecto | Qué excluye |
|---|---|---|
| Ignorar Inhabilitados | ✅ Sí | Productos marcados como inhabilitados en el sistema. |
| Ignorar Sin Stock | ✅ Sí | Productos con stock cero en toda la red. |
| Ignorar Sin Demanda | ✅ Sí | Productos con demanda presupuestada y remitida igual a cero. |
| Ignorar Inmovilizado / A Demanda | ✅ Sí | Productos con Grupo de Stock 'DNS - A Demanda' o 'DNS - Inmovilizado'. |

Además, el usuario puede seleccionar qué **familias lógicas** incluir. Por defecto se incluyen todas.

> **Nota:** Los filtros se aplican antes de cualquier cálculo. Un producto excluido no aparece en el resultado ni influye en los totales de ninguna sucursal.

---

## 4. Clasificación en Familias Lógicas

Cada producto se clasifica automáticamente según las siguientes reglas, en orden de prioridad:

| Prioridad | Familia | Condición |
|---|---|---|
| 1 | GET | subfamilia2 contiene 'GET KTN' o 'FIJACION GET' |
| 2 | RODAJE | subfamilia2 contiene 'RODAJE KTN' o 'FIJACION RODAJE' |
| 3 | DONALDSON | subfamilia principal contiene 'DONALDSON' |
| 4 | TURBO | subfamilia principal contiene 'TURBO' |
| 5 | KTN | subfamilia principal contiene 'IMPORTADOS' y la secundaria 'FILTROS KTN' |
| 6 | REPUESTOS | subfamilia2 contiene 'CAT ALTERNATIVO' o 'REPUESTOS KTN', o subfamilia contiene 'NORDIC LIGHTS' |
| 7 | OTROS | Ninguna condición anterior se cumple |

Esta clasificación determina qué regla de empaque se aplicará al calcular los envíos.

---

## 5. Coeficientes de Rotación (Wp y Wf)

Se calculan dos indicadores que se usan como insumo del Método A de estimación de demanda:

- **Wp (producto):** Remitido total / Presupuestado total del SKU. Indica la eficiencia de ejecución del presupuesto a nivel producto.
- **Wf (familia):** Igual que Wp, pero calculado sobre todos los productos de la misma familia. Representa la eficiencia promedio del grupo.

> **Ejemplo:** Si DONALDSON tuvo 850 unidades remitidas sobre 1.000 presupuestadas, Wf = 0,85. Si un producto específico tuvo Wp = 0,60 (por debajo del promedio familiar), el Método A ajustará su demanda estimada usando la eficiencia de la familia.

---

## 6. Estimación de Demanda

La demanda se estima individualmente para cada sucursal y luego se suma para obtener la demanda total de la red.

### 6.1 Método B — Histórico (Recomendado, activo por defecto)

Se basa en las cantidades efectivamente remitidas. Las reglas son:

| Situación | Demanda estimada |
|---|---|
| No hubo remisiones (rem = 0) | 50% del presupuesto (demanda latente). |
| Presupuesto superó remisiones en menos del 50% | Promedio entre presupuesto y remisiones. |
| Presupuesto superó remisiones en 50% o más | 1,5 × remisiones (controla presupuestos sobreestimados). |
| Remisiones igualaron o superaron el presupuesto | Igual a las remisiones (el dato real prevalece). |

### 6.2 Método A — Teórico (Parque)

Se basa en los coeficientes W y en las cantidades presupuestadas. Útil cuando el histórico no es representativo.

| Situación | Demanda estimada |
|---|---|
| El producto rindió menos que su familia (Wp < Wf) | Wf × Presupuesto (se usa el rendimiento promedio de la familia). |
| El producto rindió igual o mejor que su familia (Wp ≥ Wf) | 1,1 × Remisiones reales (se agrega 10% de margen). |

---

## 7. Cálculo de Coberturas y Brechas

La **cobertura** indica cuántos meses puede abastecerse una sucursal con el stock disponible, a la demanda estimada.

### 7.1 Tipos de stock considerados

- **Stock físico:** Unidades presentes en depósitos. Para SF: Stock SF + Auxiliar + SV ARG + SV MIN + NS NOA.
- **Stock ampliado:** Stock físico + tránsitos por OT pendientes + envíos entrantes ya comprometidos.

### 7.2 Coberturas objetivo

- **Origen (por defecto 6 meses):** Mínimo de stock que debe conservar el origen tras los envíos.
- **Destinos (por defecto 4 meses):** Nivel al que se busca llevar cada sucursal destino.

### 7.3 Límite global de cobertura

Para evitar sobreabastecer sucursales cuando el stock total de la red es limitado, el sistema calcula la cobertura ampliada global. Ninguna sucursal puede recibir más de lo que justifica esta cobertura: si la red entera cubre solo 3 meses, no tiene sentido apuntar a 4 meses en un destino.

### 7.4 Diferencia (Sobra / Falta)

- **Valor positivo:** La sucursal tiene más stock del objetivo → puede ceder unidades.
- **Valor negativo:** La sucursal tiene menos stock del objetivo → necesita recibir unidades.

---

## 8. Distribución de Stock — Cálculo de Envíos

Esta es la etapa final del proceso de Reposición. Para cada producto y cada sucursal destino, el sistema determina cuántas unidades enviar.

---

### 8.1 Paso 1: Disponibilidad real del origen

El sistema determina cuántas unidades puede ceder el origen, con reglas distintas según el tipo de producto:

#### 🔵 Para Filtros (DONALDSON, TURBO, KTN)

El origen retiene como mínimo el stock equivalente a **1 mes de su propia demanda**. Las unidades disponibles son las que superan esa retención, limitadas al excedente calculado sobre la cobertura ampliada.

> *Ejemplo: Si SF tiene 120 unidades de un filtro y su demanda mensual es 20, retiene 20 y pone a disposición hasta 100 (sujeto a que tenga excedente real respecto al objetivo de cobertura).*

#### 🟠 Para Rodaje y Repuestos (GET, RODAJE, REPUESTOS, OTROS)

El origen retiene al menos el equivalente a 1 mes de demanda, redondeado hacia arriba al siguiente juego completo (siempre se retiene al menos 1 juego). Las unidades disponibles se calculan restando esa retención al stock físico.

> **Restricción de seguridad:** En ningún caso se puede enviar más unidades que el stock físico real del origen, independientemente de lo que sugiera el cálculo de coberturas.

---

### 8.2 Paso 2: Necesidad de cada sucursal destino

Para cada sucursal con brecha negativa (falta stock), se calcula la cantidad a enviar, ajustada según las reglas de empaque de la familia:

#### 🔵 Filtros — Lógica de Cajas (DONALDSON, TURBO, KTN)

Los filtros se empacan en cajas de 6 o 12 unidades. Si la necesidad calculada no es múltiplo exacto del tamaño de caja, el sistema puede completar la caja si el faltante es pequeño:

| Tamaño de caja | Se completa si el faltante para cerrarla es... |
|---|---|
| Caja de 6 | 1 o 2 unidades (ej: 4→6, 5→6) |
| Caja de 12 | 1, 2 o 3 unidades (ej: 9→12, 10→12, 11→12) |

Si el faltante para cerrar la caja supera esos umbrales, se envía la cantidad exacta sin redondear hacia arriba.

#### 🟠 Rodaje y Repuestos — Lógica de Juegos/Kits (GET, RODAJE, REPUESTOS, OTROS)

Estos productos se manejan en juegos de N piezas (campo `qty_piezas` del archivo). El sistema asegura que el stock resultante en la sucursal destino sea siempre un múltiplo completo del tamaño de juego: se calcula cuántos juegos son necesarios para cubrir la necesidad y se redondea hacia arriba al siguiente juego completo.

> *Ejemplo: Si una sucursal necesita 7 unidades y el juego es de 4 piezas, se enviarán 8 (2 juegos completos).*

---

### 8.3 Paso 3: Distribución cuando el stock disponible es insuficiente

**Si hay stock suficiente:** Se envía la cantidad calculada a cada destino sin restricciones adicionales.

**Si el stock disponible es menor que la suma total de necesidades** (escasez), el sistema aplica un **prorrateo proporcional con corrección de remanentes**:

1. **Asignación proporcional base:** Cada sucursal recibe una fracción del stock disponible proporcional a su necesidad relativa. El resultado se redondea hacia abajo.
2. **Distribución del remanente:** Las unidades que "sobran" por el redondeo se distribuyen de a una, priorizando la sucursal con mayor déficit (brecha más negativa).

> Esto garantiza que ninguna sucursal quede sistemáticamente excluida y que el stock disponible se aproveche al máximo.

---

## 9. Resumen Secuencial del Proceso

| Paso | Acción | Resultado |
|---|---|---|
| 1 | Carga del archivo CSV | Dataset completo |
| 2 | Aplicar filtros | Dataset depurado |
| 3 | Clasificar por familia lógica | Familia asignada a cada SKU |
| 4 | Calcular Wp y Wf (solo Método A) | Coeficientes de rotación |
| 5 | Estimar demanda por sucursal (A o B) | Demanda anual estimada |
| 6 | Calcular stock ampliado y coberturas | Cobertura actual y objetivo |
| 7 | Calcular brecha (Sobra/Falta) | Diferencia por SKU × sucursal |
| 8A — Filtros | Calcular necesidad → redondear a caja | Unidades a enviar |
| 8B — Rodaje/Repuestos | Calcular necesidad → redondear a juego | Unidades a enviar |
| 9 | Verificar disponibilidad y prorratear si hay escasez | Envíos finales confirmados |

---

## 10. Módulo de Devolución — Identificación de Sobrantes

El modo Devolución identifica productos con exceso de stock en las sucursales (BA, MDZ, SLT) y señala oportunidades de retorno a Santa Fe. No calcula envíos: señala candidatos para rebalanceo.

### 10.1 Criterio de excedente

Un producto se considera sobrante si su cobertura actual (incluyendo tránsitos pendientes) supera el umbral configurado. El umbral por defecto equivale a **6 meses (0,5 años)** y es parametrizable.

La cantidad sugerida a devolver es la diferencia entre el stock actual y el stock ideal al umbral fijado, redondeada hacia abajo. Nunca se sugiere devolver más que el stock físico disponible.

### 10.2 Retornos prioritarios

El sistema cruza los excedentes en sucursales con la situación de Santa Fe. Si un producto **sobra en una sucursal Y falta en SF** (SF tiene menos de 6 meses de su propia demanda), ese ítem se marca como **prioritario para retorno**.

### 10.3 Información que provee el módulo

- Total de ítems con excedente por sucursal.
- Unidades sobrantes, peso (kg) y volumen (m³) estimado.
- Resumen por familia lógica.
- Detalle por SKU con stock actual, demanda estimada y excedente sugerido.
- Alerta de ítems que sirven directamente a la necesidad de Santa Fe.

---

## 11. Parámetros Configurables

| Parámetro | Por defecto | Descripción |
|---|---|---|
| Modo de análisis | Reposición (Envío) | Reposición o Devolución. |
| Sucursal origen | SF (Santa Fe) | Desde dónde se distribuye el stock. |
| Método de demanda | B (Histórico) | Criterio para estimar la demanda. |
| Cobertura objetivo — Origen | 6 meses | Mínimo que debe conservar el origen tras los envíos. |
| Cobertura objetivo — Destinos | 4 meses | Nivel al que se busca llevar cada sucursal destino. |
| Ignorar Inhabilitados | Activo | Excluye productos inhabilitados. |
| Ignorar Sin Stock | Activo | Excluye productos sin stock en ninguna sucursal. |
| Ignorar Sin Demanda | Activo | Excluye productos sin señal de demanda. |
| Ignorar Inmovilizado/A Demanda | Activo | Excluye productos DNS. |
| Familias incluidas | Todas | Selección de familias lógicas. |
| Umbral de exceso (Devolución) | 0,5 (6 meses) | Cobertura a partir de la cual se considera sobrante. |

---

## 12. Glosario

| Término | Definición |
|---|---|
| Cobertura | Meses que puede abastecerse una sucursal con su stock actual a la demanda estimada. |
| Cobertura ampliada | Cobertura incluyendo tránsitos pendientes de llegada. |
| Brecha (Sobra/Falta) | Diferencia entre stock disponible y stock objetivo. Negativo = falta; positivo = sobra. |
| Demanda estimada | Proyección anual de unidades a colocar en una sucursal. |
| Wp | Coeficiente de rotación del producto: remitido / presupuestado a nivel SKU. |
| Wf | Coeficiente de rotación de la familia: remitido / presupuestado a nivel familia lógica. |
| Juego (Kit) | Conjunto de N piezas que deben manejarse como unidad indivisible (Rodaje/Repuestos). |
| Caja | Unidad de empaque para filtros: 6 o 12 unidades según el producto. |
| OT (Orden de Traslado) | Movimiento de stock interno ya iniciado pero no recibido aún. |
| DNS | 'Disponible No Stocked'. Productos de gestión especial no reponibles automáticamente. |
| Stock físico SF | Stock SF + Auxiliar + SV ARG + SV MIN + NS NOA. |
