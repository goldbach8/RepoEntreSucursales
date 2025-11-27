SELECT
    productos.Código,

    CAST(productos.descripcion AS VARCHAR(200)) as Descripción,

    CAST(productos.descripcion2 AS VARCHAR(200)) as Descripción2,


    ROUND(ISNULL(PresSF.QPresSF,0) + ISNULL(PresSalta.QPresSLT,0) + ISNULL(PresBA.QPresBA,0) + ISNULL(PresMDZ.QPresMDZ,0),2) AS 'QPres Total',
    ROUND(ISNULL(RemSF.QRemSF,0) + ISNULL(RemSLT.QRemSLT,0) + ISNULL(RemBa.QRemBA,0) + ISNULL(RemMDZ.QRemMDZ,0) + ISNULL(RemNSNOA_mansfield.QRemNSNOA_Mansfield,0) + ISNULL(RemNSNOA.QRemNSNOA,0),2) AS 'QRem Total',

    '' as 'D.EST Total',

    ROUND(ISNULL(DepSF.[Stock SF],0)+ISNULL(DepBA.[Stock BA],0)+ISNULL(DepCE.[Stock CE],0)+ISNULL(DepMDZ.[Stock MDZ],0)+ISNULL(DepSLT.[Stock SLT],0)+ISNULL(DepAux.[Stock AUX],0)+ISNULL(DepSVMin.[Stock SV MIN],0)+ISNULL(DepSVArg.[Stock SV ARG],0)+ISNULL(DepNSNOA.[Stock NS NOA],0),2) AS 'Stock Total',
    '' AS 'Cobertura Anual',

    ISNULL(PresSF.QPresSF,0) AS 'QPresSF',
    ISNULL(RemSF.QRemSF,0)+ISNULL(RemNSNOA.QRemNSNOA,0) AS 'QRemSF',
    '' as 'D.EST SF',
    '' as 'STOCK SF FINAL',
    ISNULL(DepSF.[Stock SF],0)+ISNULL(DepCE.[Stock CE],0) AS 'Stock SF',
    ISNULL(DepAUX.[Stock AUX],0) AS 'Stock AUX',
    ISNULL(DepSVArg.[Stock SV ARG],0) AS 'Stock SV ARG',
    ISNULL(DepSVMin.[Stock SV MIN],0) AS 'Stock SV MIN',
    ISNULL(DepNSNOA.[Stock NS NOA],0) AS 'Stock NS NOA',
    '' AS 'Sobra / Falta',

    ISNULL(PresBA.QPresBA,0) AS 'QPresBA',
    ISNULL(RemBa.QRemBA,0) AS 'QRemBA',
    '' as 'D.EST BA',
    ISNULL(Depba.[Stock BA],0) AS 'Stock BA',
    '' AS 'Sobra / Falta',

    ISNULL(PresMDZ.QPresMDZ,0) AS 'QPresMDZ',
    ISNULL(RemMDZ.QRemMDZ,0) AS 'QRemMDZ',
    '' as 'D.EST MDZ',
    ISNULL(DepMDZ.[Stock MDZ],0) AS 'Stock MDZ',
    '' AS 'Sobra / Falta',

    ISNULL(PresSalta.QPresSLT,0) AS 'QPresSLT',
    ISNULL(RemSLT.QRemSLT,0)+ISNULL(RemNSNOA_mansfield.QRemNSNOA_Mansfield,0) AS 'QRemSLT',
    '' as 'D.EST SALTA',
    ISNULL(DepSLT.[Stock SLT],0) AS 'Stock SLT',
    '' AS 'Sobra / Falta',

    CASE WHEN Familia IS NULL THEN '' ELSE Familia END AS Familia,
    CASE WHEN Familia.SubFamilia IS NULL THEN '' ELSE Familia.SubFamilia END AS SubFamilia,
    CASE WHEN Familia.SubFamilia2 IS NULL THEN '' ELSE Familia.SubFamilia2 END AS SubFamilia2,
    CASE productos.Inhabilitado WHEN 1 THEN 'Si' ELSE 'No' END AS Inhabilitado,
    productosstock.UnidadStock AS 'Grupo Stock',
    productosstock.peso AS Peso,
    productosstock.cantidadpiezas as 'Qty Piezas',
	info.campo20 AS Volumen
FROM productos
LEFT JOIN info on info.IDRef = productos.RecID
    LEFT JOIN productosstock on productosstock.IDProducto = productos.RecID
    LEFT JOIN

    (SELECT IDproducto, SUM(Cantidad) AS 'QPresSF'
    FROM presupuestositems
        LEFT JOIN presupuestos on presupuestos.RecID = presupuestositems.IDPresupuesto
        LEFT JOIN contactos ON contactos.IDContacto = presupuestos.IDRef
        LEFT JOIN empresas ON empresas.IDEmpresa = contactos.IDEmpresa
    WHERE 
			presupuestos.fechacreacion >= DATEADD(day,-365, GETDATE()) AND

        (empresas.Calificacion = 'TALLER' OR empresas.Calificacion = 'CORDOBA' OR
        empresas.Calificacion = 'FERNANDO GARCIA' OR empresas.Calificacion = 'SANTA FE' OR
        empresas.Calificacion = 'MINERIA' OR empresas.Calificacion = 'NEA' OR
        empresas.Calificacion = 'MOSTRADOR' OR empresas.Calificacion = 'RENTAL' OR
        empresas.Calificacion = 'CENTRO')

        AND

        (	MotivoCierre<>'Pasado a otra empresa' or
        MotivoCierre<>'INFORMATIVO - ESTIMATIVO (DUPLICADO/ERROR/REPETIDO/NO CONSIDERAR)' or
        MotivoCierre<>'ERROR EN CODIGO SOLICITADO'or
        MotivoCierre<>'DUPLICADO'
			)
    GROUP BY IDProducto	) AS PresSF on PresSF.IDProducto = productos.RecID



    LEFT JOIN (SELECT IDproducto, SUM(Cantidad) AS 'QPresSLT'
    FROM presupuestositems
        LEFT JOIN presupuestos ON presupuestositems.IDPresupuesto = presupuestos.RecID
        LEFT JOIN contactos ON contactos.IDContacto = presupuestos.IDRef
        LEFT JOIN empresas ON empresas.IDEmpresa = contactos.IDEmpresa

    WHERE 
			presupuestos.fechacreacion >= DATEADD(day,-365, GETDATE()) AND

        empresas.Calificacion = 'NOA' AND

        (	
				MotivoCierre<>'Pasado a otra empresa' or
        MotivoCierre<>'INFORMATIVO - ESTIMATIVO (DUPLICADO/ERROR/REPETIDO/NO CONSIDERAR)' or
        MotivoCierre<>'ERROR EN CODIGO SOLICITADO'or
        MotivoCierre<>'DUPLICADO'
			)
    GROUP BY IDProducto) AS PresSalta ON PresSalta.IDProducto = productos.RecID

    LEFT JOIN (SELECT IDProducto, SUM(Cantidad) AS 'QPresBA'
    FROM presupuestositems
        LEFT JOIN presupuestos ON presupuestositems.IDPresupuesto = presupuestos.RecID
        LEFT JOIN contactos ON contactos.IDContacto = presupuestos.IDRef
        LEFT JOIN empresas ON empresas.IDEmpresa = contactos.IDEmpresa
    WHERE presupuestos.fechacreacion  >= DATEADD(day,-365, GETDATE())
        AND (empresas.Calificacion = 'BA' OR empresas.Calificacion = 'CABA' OR empresas.Calificacion = 'PBA' OR empresas.Calificacion = 'RP')
        AND
        (	MotivoCierre<>'Pasado a otra empresa' or
        MotivoCierre<>'INFORMATIVO - ESTIMATIVO (DUPLICADO/ERROR/REPETIDO/NO CONSIDERAR)' or
        MotivoCierre<>'ERROR EN CODIGO SOLICITADO'or
        MotivoCierre<>'DUPLICADO'
		)
    GROUP BY IDProducto) AS PresBA ON PresBA.IDProducto=productos.RecID

    LEFT JOIN (SELECT IdProducto, SUM(Cantidad) AS 'QPresMDZ'
    FROM presupuestositems
        LEFT JOIN presupuestos ON presupuestositems.IDPresupuesto = presupuestos.RecID
        LEFT JOIN contactos ON contactos.IDContacto = presupuestos.IDRef
        LEFT JOIN empresas ON empresas.IDEmpresa = contactos.IDEmpresa
    WHERE presupuestos.fechacreacion  >= DATEADD(day,-365, GETDATE())
        AND empresas.Calificacion = 'CUYO'
        and
        (	MotivoCierre<>'Pasado a otra empresa' or
        MotivoCierre<>'INFORMATIVO - ESTIMATIVO (DUPLICADO/ERROR/REPETIDO/NO CONSIDERAR)' or
        MotivoCierre<>'ERROR EN CODIGO SOLICITADO'or
        MotivoCierre<>'DUPLICADO'
		)
    GROUP BY IDProducto) AS PresMDZ ON PresMDZ.IDProducto = productos.RecID

    --Calculos de Remito---------------------------------------------------------------------

    LEFT JOIN (
			SELECT
        Remitositems.IDProducto,
        SUM(remitositems.Cantidad) -SUM(ISNULL(entregasitems.Cantidad,0)) AS 'QRemSLT'
    FROM remitositems

        LEFT JOIN remitos on remitos.RecID = remitositems.IDRemito
        LEFT JOIN fiscal ON fiscal.RecID = remitos.IDFiscal
        LEFT JOIN empresas ON empresas.IDEmpresa = fiscal.IDRef
        LEFT JOIN itemsstock on itemsstock.IDRefProd = remitositems.RecID
        LEFT JOIN productosdepositos pd on pd.RecID = itemsstock.IDDeposito
        LEFT JOIN entregasitems on entregasitems.IDRemitoProd = remitositems.RecID

    WHERE remitos.Estado <> 2 AND
        remitos.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
        AND pd.Deposito='SALTA'
        AND remitos.IDFiscal NOT IN (SELECT RECID
        FROM FiscalesSistema)
    GROUP BY remitositems.IDProducto) AS RemSLT on RemSLT.idproducto = productos.recid


    LEFT JOIN (
			SELECT
        Remitositems.IDProducto,
        SUM(remitositems.Cantidad) -SUM(ISNULL(entregasitems.Cantidad,0)) AS 'QRemBA'
    FROM remitositems

        LEFT JOIN remitos on remitos.RecID = remitositems.IDRemito
        LEFT JOIN fiscal ON fiscal.RecID = remitos.IDFiscal
        LEFT JOIN empresas ON empresas.IDEmpresa = fiscal.IDRef
        LEFT JOIN itemsstock on itemsstock.IDRefProd = remitositems.RecID
        LEFT JOIN productosdepositos pd on pd.RecID = itemsstock.IDDeposito
        LEFT JOIN entregasitems on entregasitems.IDRemitoProd = remitositems.RecID

    WHERE remitos.Estado <> 2 AND
        remitos.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
        AND pd.Deposito='BA'
        AND remitos.IDFiscal NOT IN (SELECT RECID
        FROM FiscalesSistema)
    GROUP BY remitositems.IDProducto) AS RemBA on RemBA.idproducto = productos.recid


    LEFT JOIN (
			SELECT
        Remitositems.IDProducto,
        SUM(remitositems.Cantidad) -SUM(ISNULL(entregasitems.Cantidad,0)) AS 'QRemSF'
    FROM remitositems

        LEFT JOIN remitos on remitos.RecID = remitositems.IDRemito
        LEFT JOIN fiscal ON fiscal.RecID = remitos.IDFiscal
        LEFT JOIN empresas ON empresas.IDEmpresa = fiscal.IDRef
        LEFT JOIN itemsstock on itemsstock.IDRefProd = remitositems.RecID
        LEFT JOIN productosdepositos pd on pd.RecID = itemsstock.IDDeposito
        LEFT JOIN entregasitems on entregasitems.IDRemitoProd = remitositems.RecID

    WHERE remitos.Estado <> 2 AND
        remitos.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
        AND pd.Deposito IN ('SF','CE','SV MIN','SV ARG')
        AND remitos.IDFiscal NOT IN (SELECT RECID
        FROM FiscalesSistema)
    GROUP BY remitositems.IDProducto) AS RemSF on RemSF.idproducto = productos.recid

    LEFT JOIN (
			SELECT
        Remitositems.IDProducto,
        SUM(remitositems.Cantidad) -SUM(ISNULL(entregasitems.Cantidad,0)) AS 'QRemMDZ'
    FROM remitositems

        LEFT JOIN remitos on remitos.RecID = remitositems.IDRemito
        LEFT JOIN fiscal ON fiscal.RecID = remitos.IDFiscal
        LEFT JOIN empresas ON empresas.IDEmpresa = fiscal.IDRef
        LEFT JOIN itemsstock on itemsstock.IDRefProd = remitositems.RecID
        LEFT JOIN productosdepositos pd on pd.RecID = itemsstock.IDDeposito
        LEFT JOIN entregasitems on entregasitems.IDRemitoProd = remitositems.RecID

    WHERE remitos.Estado <> 2 AND
        remitos.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
        AND pd.Deposito='MDZ'
        AND remitos.IDFiscal NOT IN (SELECT RECID
        FROM FiscalesSistema)
    GROUP BY remitositems.IDProducto) AS RemMDZ on RemMDZ.idproducto = productos.recid

    LEFT JOIN (
			SELECT
        Remitositems.IDProducto,
        SUM(remitositems.Cantidad) -SUM(ISNULL(entregasitems.Cantidad,0)) AS 'QRemNSNOA_Mansfield'
    FROM remitositems

        LEFT JOIN remitos on remitos.RecID = remitositems.IDRemito
        LEFT JOIN fiscal ON fiscal.RecID = remitos.IDFiscal
        LEFT JOIN empresas ON empresas.IDEmpresa = fiscal.IDRef
        LEFT JOIN itemsstock on itemsstock.IDRefProd = remitositems.RecID
        LEFT JOIN productosdepositos pd on pd.RecID = itemsstock.IDDeposito
        LEFT JOIN entregasitems on entregasitems.IDRemitoProd = remitositems.RecID

    WHERE remitos.Estado <> 2 AND
        remitos.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
        AND pd.Deposito='NS NOA'
        AND remitos.IDFiscal NOT IN (SELECT RECID
        FROM FiscalesSistema)
        AND remitos.IDFiscal = '86(6.q!;!!|°'
    GROUP BY remitositems.IDProducto) AS RemNSNOA_mansfield on RemNSNOA_mansfield.idproducto = productos.recid

    LEFT JOIN (
			SELECT
        Remitositems.IDProducto,
        SUM(remitositems.Cantidad) -SUM(ISNULL(entregasitems.Cantidad,0)) AS 'QRemNSNOA'
    FROM remitositems

        LEFT JOIN remitos on remitos.RecID = remitositems.IDRemito
        LEFT JOIN fiscal ON fiscal.RecID = remitos.IDFiscal
        LEFT JOIN empresas ON empresas.IDEmpresa = fiscal.IDRef
        LEFT JOIN itemsstock on itemsstock.IDRefProd = remitositems.RecID
        LEFT JOIN productosdepositos pd on pd.RecID = itemsstock.IDDeposito
        LEFT JOIN entregasitems on entregasitems.IDRemitoProd = remitositems.RecID

    WHERE remitos.Estado <> 2 AND
        remitos.FechaEmision >= DATEADD(YEAR, -1, GETDATE())
        AND pd.Deposito='NS NOA'
        AND remitos.IDFiscal NOT IN (SELECT RECID
        FROM FiscalesSistema)
        AND remitos.IDFiscal <> '86(6.q!;!!|°'
    GROUP BY remitositems.IDProducto) AS RemNSNOA on RemNSNOA.idproducto = productos.recid


    --Calculos de Stock----------------------------------------------------------------------

    left join
    (SELECT idproducto, Deposito as 'Deposito CE',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock CE'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='CE'
    GROUP BY idproducto,Deposito) as DepCE ON DepCE.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito SF',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock SF'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='SF'
    GROUP BY idproducto,Deposito) as DepSF ON DepSF.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito BA',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock BA'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='BA'
    GROUP BY idproducto,Deposito) as DepBA ON DepBA.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito MDZ',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock MDZ'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='MDZ'
    GROUP BY idproducto,Deposito) as DepMDZ ON DepMDZ.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito AUX',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock AUX'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='AUX'
    GROUP BY idproducto,Deposito) as DepAux ON DepAux.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito SV ARG',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock SV ARG'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='SV ARG'
    GROUP BY idproducto,Deposito) as DepSVArg ON DepSVArg.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito SV MIN',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock SV MIN'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='SV MIN'
    GROUP BY idproducto,Deposito) as DepSVMin ON DepSVMin.idproducto = productos.RecID

    LEFT JOIN
    (SELECT idproducto, Deposito AS 'Deposito NS NOA',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock NS NOA'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='NS NOA'
    GROUP BY idproducto,Deposito) as DepNSNOA ON DepNSNOA.idproducto = productos.RecID

    left join
    (SELECT idproducto, Deposito as 'Deposito SLT',
        SUM(CASE TIPO WHEN 0 THEN (cantidad*Equivalencia) WHEN 1 THEN -(cantidad*Equivalencia) ELSE 0 END) AS 'Stock SLT'
    FROM productosstockmovimientos
        INNER JOIN productos ON productosstockmovimientos.idproducto = productos.recid
        LEFT JOIN productosdepositos ON productosstockmovimientos.IDDeposito=productosdepositos.RecID
    where Deposito='SALTA'
    GROUP BY idproducto,Deposito) as DepSLT ON DepSLT.idproducto = productos.RecID
    left join
    (SELECT
        productos.FechaCreacion,
        empresas.Empresa AS Fabricante,
        CASE
                WHEN arbolcarpetas_5.Nivel = 0 THEN arbolcarpetas_5.Nombre
                WHEN arbolcarpetas_5.Nivel = 1 THEN arbolcarpetas_1.Nombre
                WHEN arbolcarpetas_5.Nivel = 2 THEN arbolcarpetas_2.Nombre
                WHEN arbolcarpetas_5.Nivel = 3 THEN arbolcarpetas_3.Nombre
                ELSE arbolcarpetas_4.Nombre
            END AS Familia,

        CASE
                WHEN arbolcarpetas_5.Nivel = 0 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 1 THEN arbolcarpetas_5.Nombre
                WHEN arbolcarpetas_5.Nivel = 2 THEN arbolcarpetas_1.Nombre
                WHEN arbolcarpetas_5.Nivel = 3 THEN arbolcarpetas_2.Nombre
                ELSE arbolcarpetas_3.Nombre
            END AS SubFamilia,

        CASE
                WHEN arbolcarpetas_5.Nivel = 0 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 1 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 2 THEN arbolcarpetas_5.Nombre
                WHEN arbolcarpetas_5.Nivel = 3 THEN arbolcarpetas_1.Nombre
                ELSE arbolcarpetas_2.Nombre
            END AS SubFamilia2,

        CASE
                WHEN arbolcarpetas_5.Nivel = 0 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 1 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 2 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 3 THEN arbolcarpetas_5.Nombre
                ELSE arbolcarpetas_1.Nombre
            END AS SubFamilia3,
        CASE
                WHEN arbolcarpetas_5.Nivel = 0 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 1 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 2 THEN NULL
                WHEN arbolcarpetas_5.Nivel = 3 THEN NULL
                ELSE arbolcarpetas_5.Nombre
            END AS SubFamilia4,
        productos.RecID
    FROM
        arbolcarpetas AS arbolcarpetas_2
        RIGHT OUTER JOIN arbolcarpetas AS arbolcarpetas_1
        RIGHT OUTER JOIN productos
        INNER JOIN arbolcarpetas AS arbolcarpetas_5 ON productos.IDCarpeta = arbolcarpetas_5.RecID ON arbolcarpetas_1.RecID = arbolcarpetas_5.IDPadre
        LEFT OUTER JOIN empresas ON productos.IDFabricante = empresas.IDEmpresa ON arbolcarpetas_2.RecID = arbolcarpetas_1.IDPadre
        LEFT OUTER JOIN arbolcarpetas AS arbolcarpetas_3
        LEFT OUTER JOIN arbolcarpetas AS arbolcarpetas_4 ON arbolcarpetas_3.IDPadre = arbolcarpetas_4.RecID
        LEFT OUTER JOIN arbolcarpetas ON arbolcarpetas_4.IDPadre = arbolcarpetas.RecID ON arbolcarpetas_2.IDPadre = arbolcarpetas_3.RecID) 
    as Familia ON familia.recid = productos.RecID

WHERE
productos.Estado = 0
ORDER BY  Codigo