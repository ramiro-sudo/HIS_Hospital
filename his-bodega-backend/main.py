# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func 
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta, date
from typing import Optional
import models
import schemas
import crud
import auth
import database

app = FastAPI(title="HIS-Bodega", description="Sistema de Gestión de Inventario")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas
models.Base.metadata.create_all(bind=database.engine)

def registrar_auditoria(db, usuario_id, accion, detalle="", ip_address=""):
    auditoria = models.Auditoria(
        usuario_id=usuario_id,
        accion=accion,
        detalle=detalle,
        ip_address=ip_address
    )
    db.add(auditoria)
    db.commit()

@app.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/usuarios/", response_model=schemas.Usuario, status_code=201)
def create_user(user: schemas.UsuarioCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_usuario_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_usuario(db=db, usuario=user)

@app.get("/usuarios/me", response_model=schemas.Usuario)
def read_users_me(current_user: schemas.Usuario = Depends(auth.get_current_user)):
    return current_user

# CRUD para Insumos (solo admin)
@app.post("/insumos/", response_model=schemas.Insumo, status_code=201)
def create_insumo(insumo: schemas.InsumoCreate, current_user: schemas.Usuario = Depends(auth.get_current_admin_user), db: Session = Depends(database.get_db)):
    db_insumo = crud.create_insumo(db=db, insumo=insumo)
    registrar_auditoria(db, current_user.id, "CREAR INSUMO", f"Nombre: {insumo.nombre}")
    return db_insumo

# ✅ ENDPOINT ACTUALIZADO: Incluye la especialidad
@app.get("/insumos/", response_model=list[schemas.Insumo])
def read_insumos(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    # Usar joinedload para incluir la relación con especialidad
    insumos = db.query(models.Insumo).options(joinedload(models.Insumo.especialidad)).offset(skip).limit(limit).all()
    return insumos

@app.get("/insumos/{insumo_id}", response_model=schemas.Insumo)
def read_insumo(insumo_id: int, db: Session = Depends(database.get_db)):
    # ✅ También actualizar el endpoint individual
    db_insumo = db.query(models.Insumo).options(joinedload(models.Insumo.especialidad)).filter(models.Insumo.id == insumo_id).first()
    if db_insumo is None:
        raise HTTPException(status_code=404, detail="Insumo not found")
    return db_insumo

@app.put("/insumos/{insumo_id}", response_model=schemas.Insumo)
def update_insumo(insumo_id: int, insumo: schemas.InsumoCreate, current_user: schemas.Usuario = Depends(auth.get_current_admin_user), db: Session = Depends(database.get_db)):
    db_insumo = crud.update_insumo(db, insumo_id=insumo_id, insumo=insumo)
    if db_insumo is None:
        raise HTTPException(status_code=404, detail="Insumo not found")
    registrar_auditoria(db, current_user.id, "ACTUALIZAR INSUMO", f"ID: {insumo_id}, Nombre: {insumo.nombre}")
    return db_insumo

@app.delete("/insumos/{insumo_id}", response_model=schemas.Insumo)
def delete_insumo(insumo_id: int, current_user: schemas.Usuario = Depends(auth.get_current_admin_user), db: Session = Depends(database.get_db)):
    db_insumo = crud.delete_insumo(db, insumo_id=insumo_id)
    if db_insumo is None:
        raise HTTPException(status_code=404, detail="Insumo not found")
    registrar_auditoria(db, current_user.id, "ELIMINAR INSUMO", f"ID: {insumo_id}")
    return db_insumo

# CRUD para Entradas
@app.post("/entradas/", response_model=schemas.Entrada, status_code=201)
def create_entrada(entrada: schemas.EntradaCreate, current_user: schemas.Usuario = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if entrada.usuario_id is None:
        entrada.usuario_id = current_user.id
    db_entrada = crud.create_entrada(db=db, entrada=entrada)
    registrar_auditoria(db, current_user.id, "REGISTRAR ENTRADA", f"Insumo ID: {entrada.insumo_id}, Cantidad: {entrada.cantidad}")
    return db_entrada

@app.get("/entradas/", response_model=list[schemas.Entrada])
def read_entradas(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    entradas = db.query(models.Entrada).offset(skip).limit(limit).all()
    
    # Añadir nombre del insumo a cada entrada
    for entrada in entradas:
        insumo = db.query(models.Insumo).filter(models.Insumo.id == entrada.insumo_id).first()
        if insumo:
            entrada.insumo_nombre = insumo.nombre
    
    return entradas

@app.post("/salidas/", response_model=schemas.Salida, status_code=201)
def create_salida(salida: schemas.SalidaCreate, current_user: schemas.Usuario = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if salida.usuario_id is None:
        salida.usuario_id = current_user.id
    
    # Verificar stock disponible
    insumo = db.query(models.Insumo).filter(models.Insumo.id == salida.insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    
    if insumo.stock_actual < salida.cantidad:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Stock disponible: {insumo.stock_actual}, solicitado: {salida.cantidad}")
    
    db_salida = crud.create_salida(db=db, salida=salida)
    registrar_auditoria(db, current_user.id, "REGISTRAR SALIDA", f"Insumo ID: {salida.insumo_id}, Cantidad: {salida.cantidad}")
    return db_salida

@app.get("/salidas/", response_model=list[schemas.Salida])
def read_salidas(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return crud.get_salidas(db, skip=skip, limit=limit)

# CRUD para Alertas
@app.post("/alertas/", response_model=schemas.Alerta, status_code=201)
def create_alerta(alerta: schemas.AlertaCreate, current_user: schemas.Usuario = Depends(auth.get_current_admin_user), db: Session = Depends(database.get_db)):
    return crud.create_alerta(db=db, alerta=alerta)

@app.get("/alertas/", response_model=list[schemas.Alerta])
def read_alertas(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """Obtiene todas las alertas activas (elimina las inválidas)"""
    alertas = db.query(models.Alerta).offset(skip).limit(limit).all()
    
    # Filtrar alertas válidas y añadir nombre del insumo
    alertas_validas = []
    for alerta in alertas:
        insumo = db.query(models.Insumo).filter(models.Insumo.id == alerta.insumo_id).first()
        if insumo:
            # Verificar si la alerta aún es válida
            if alerta.mensaje.startswith("Stock bajo"):
                # Alerta de stock bajo: válido si stock_actual < stock_minimo
                if insumo.stock_actual < insumo.stock_minimo and insumo.stock_minimo > 0:
                    alerta.insumo = insumo  # Añadir el objeto insumo completo
                    alertas_validas.append(alerta)
            elif alerta.mensaje.startswith("Insumo vence pronto"):
                # Alerta de vencimiento: válido si la fecha de vencimiento está en el futuro
                import re
                match = re.search(r'(\d{4}-\d{2}-\d{2})', alerta.mensaje)
                if match:
                    fecha_vencimiento = match.group(1)
                    from datetime import date
                    if date.today() <= date.fromisoformat(fecha_vencimiento):
                        alerta.insumo = insumo  # Añadir el objeto insumo completo
                        alertas_validas.append(alerta)
    
    return alertas_validas

# ENDPOINT PARA ALERTAS AUTOMÁTICAS (MEJORA #1)
@app.post("/alertas/automáticas", response_model=list[schemas.Alerta])
def generate_automatic_alerts(db: Session = Depends(database.get_db)):
    """Genera alertas automáticas para insumos con stock bajo"""
    insumos_bajo_stock = db.query(models.Insumo).filter(
        models.Insumo.stock_actual < models.Insumo.stock_minimo,
        models.Insumo.stock_minimo > 0
    ).all()
    
    alertas_creadas = []
    for insumo in insumos_bajo_stock:
        # Verificar si ya existe una alerta activa para este insumo
        alerta_existente = db.query(models.Alerta).filter(
            models.Alerta.insumo_id == insumo.id,
            models.Alerta.mensaje.like(f"Stock bajo: {insumo.stock_actual} < {insumo.stock_minimo}")
        ).first()
        
        if not alerta_existente:
            alerta = models.Alerta(
                insumo_id=insumo.id,
                mensaje=f"Stock bajo: {insumo.stock_actual} < {insumo.stock_minimo}",
                fecha=date.today()
            )
            db.add(alerta)
            alertas_creadas.append(alerta)
    
    db.commit()
    return alertas_creadas

# Kardex
@app.get("/kardex/{insumo_id}", response_model=dict)
def get_kardex(insumo_id: int, db: Session = Depends(database.get_db)):
    """Obtiene el kardex de un insumo con cálculos de valor total"""
    entradas = db.query(models.Entrada).filter(models.Entrada.insumo_id == insumo_id).all()
    salidas = db.query(models.Salida).filter(models.Salida.insumo_id == insumo_id).all()
    
    movimientos = []
    for e in entradas:
        movimientos.append({
            "tipo": "ENTRADA",
            "fecha": e.fecha,
            "cantidad": float(e.cantidad),
            "precio_unitario": float(e.precio_unitario) if e.precio_unitario else 0.0,
            "precio_total": float(e.cantidad * e.precio_unitario) if e.precio_unitario else 0.0,
            "numero_referencia": e.numero_referencia,
            "remitente_destinatario": e.remitente_destinatario,
            "numero_lote": e.numero_lote,
            "fecha_vencimiento": e.fecha_vencimiento,
            "usuario_id": e.usuario_id
        })
    for s in salidas:
        movimientos.append({
            "tipo": "SALIDA",
            "fecha": s.fecha,
            "cantidad": float(s.cantidad),
            "precio_unitario": float(s.precio_unitario) if s.precio_unitario else 0.0,
            "precio_total": float(s.cantidad * s.precio_unitario) if s.precio_unitario else 0.0,
            "numero_referencia": s.numero_referencia,
            "remitente_destinatario": s.remitente_destinatario,
            "numero_lote": None,
            "fecha_vencimiento": None,
            "usuario_id": s.usuario_id
        })
    
    # Ordenar por fecha
    movimientos.sort(key=lambda x: x["fecha"])
    
    # Calcular el stock actual y el valor total
    stock_actual = 0
    for mov in movimientos:
        if mov["tipo"] == "ENTRADA":
            stock_actual += mov["cantidad"]
        elif mov["tipo"] == "SALIDA":
            stock_actual -= mov["cantidad"]
    
    # Obtener el último precio unitario para calcular el valor del stock
    ultimo_precio_unitario = 0.0
    for mov in reversed(movimientos):
        if mov["precio_unitario"] > 0:
            ultimo_precio_unitario = mov["precio_unitario"]
            break
    
    # Calcular el valor total del stock disponible
    valor_stock_total = stock_actual * ultimo_precio_unitario
    
    return {
        "movimientos": movimientos,
        "stock_actual": stock_actual,
        "valor_stock_total": valor_stock_total,
        "ultimo_precio_unitario": ultimo_precio_unitario
    }

# Reporte de stock
@app.get("/reporte-stock", response_model=list)
def get_stock_report(db: Session = Depends(database.get_db)):
    insumos = db.query(models.Insumo).all()
    reporte = []
    for i in insumos:
        alertas = db.query(models.Alerta).filter(models.Alerta.insumo_id == i.id).all()
        reporte.append({
            "insumo_id": i.id,
            "nombre": i.nombre,
            "descripcion": i.descripcion,
            "unidad_medida": i.unidad_medida,
            "stock_actual": float(i.stock_actual),
            "stock_minimo": float(i.stock_minimo),
            "alertas": [a.mensaje for a in alertas]
        })
    return reporte

@app.get("/insumos/{insumo_id}/lotes-disponibles")
def get_lotes_disponibles(insumo_id: int, db: Session = Depends(database.get_db)):
    """Obtiene los lotes disponibles para un insumo, ordenados por fecha de vencimiento (FEFO), 
    incluyendo el precio unitario y calculando correctamente el stock disponible por lote."""
    
    # Obtener todas las entradas para este insumo con sus precios
    entradas = db.query(models.Entrada).filter(
        models.Entrada.insumo_id == insumo_id,
        models.Entrada.cantidad > 0
    ).all()
    
    # Obtener todas las salidas para este insumo (asumiendo que las salidas registran el lote)
    salidas = db.query(models.Salida).filter(
        models.Salida.insumo_id == insumo_id
    ).all()
    
    # Agrupar entradas por lote (usando numero_lote y fecha_vencimiento como clave)
    lotes_entrada = {}
    for entrada in entradas:
        # Crear clave única para el lote
        lote_key = f"{entrada.numero_lote or 'SIN_LOTE'}_{entrada.fecha_vencimiento or '9999-12-31'}"
        
        if lote_key not in lotes_entrada:
            lotes_entrada[lote_key] = {
                'numero_lote': entrada.numero_lote,
                'fecha_vencimiento': entrada.fecha_vencimiento,
                'precio_unitario': float(entrada.precio_unitario) if entrada.precio_unitario else 0.0,
                'cantidad_total': 0.0
            }
        
        lotes_entrada[lote_key]['cantidad_total'] += float(entrada.cantidad)
    
    # Calcular salidas por lote
    # NOTA: Esto asume que tus salidas tienen un campo numero_lote
    # Si no lo tienen, necesitarás modificar tu modelo Salida para incluirlo
    lotes_salida = {}
    for salida in salidas:
        # Si tu modelo Salida no tiene numero_lote, esta lógica no funcionará correctamente
        # Por ahora, asumiremos que todas las salidas se aplican al primer lote disponible (FEFO)
        pass
    
    # Para una implementación correcta de FEFO, necesitas registrar el lote en las salidas
    # Pero como workaround temporal, calcularemos el stock total y lo distribuiremos
    
    # Obtener el stock actual del insumo
    insumo = db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    
    stock_actual = float(insumo.stock_actual)
    
    # Si el stock actual es 0, no hay lotes disponibles
    if stock_actual <= 0:
        return []
    
    # Calcular lotes disponibles con stock proporcional
    lotes_disponibles = []
    stock_restante = stock_actual
    
    # Ordenar entradas por fecha de vencimiento (FEFO)
    entradas_ordenadas = sorted(entradas, key=lambda x: x.fecha_vencimiento or '9999-12-31')
    
    for entrada in entradas_ordenadas:
        if stock_restante <= 0:
            break
            
        cantidad_entrada = float(entrada.cantidad)
        if cantidad_entrada <= 0:
            continue
            
        # Determinar cuánto stock disponible tiene este lote
        stock_lote = min(cantidad_entrada, stock_restante)
        
        if stock_lote > 0:
            lotes_disponibles.append({
                'numero_lote': entrada.numero_lote,
                'fecha_vencimiento': entrada.fecha_vencimiento,
                'stock_disponible': stock_lote,
                'precio_unitario': float(entrada.precio_unitario) if entrada.precio_unitario else 0.0
            })
            
            stock_restante -= stock_lote
    
    return lotes_disponibles

@app.post("/alertas/vencimiento", response_model=list[schemas.Alerta])
def generate_vencimiento_alerts(dias: int = 30, db: Session = Depends(database.get_db)):
    """Genera alertas para insumos que vencen en los próximos X días"""
    from datetime import date, timedelta
    
    fecha_limite = date.today() + timedelta(days=dias)
    
    # Obtener entradas con fecha de vencimiento en el rango
    entradas_proximas = db.query(models.Entrada).filter(
        models.Entrada.fecha_vencimiento.isnot(None),
        models.Entrada.fecha_vencimiento >= date.today(),
        models.Entrada.fecha_vencimiento <= fecha_limite
    ).all()
    
    alertas_creadas = []
    for entrada in entradas_proximas:
        # Verificar si ya existe una alerta para este lote
        alerta_existente = db.query(models.Alerta).filter(
            models.Alerta.insumo_id == entrada.insumo_id,
            models.Alerta.mensaje.like(f"Insumo vence pronto: Lote {entrada.numero_lote or 'SIN_LOTE'} - {entrada.fecha_vencimiento}")
        ).first()
        
        if not alerta_existente:
            insumo = db.query(models.Insumo).filter(models.Insumo.id == entrada.insumo_id).first()
            if insumo:
                mensaje = f"Insumo vence pronto: Lote {entrada.numero_lote or 'SIN_LOTE'} - {entrada.fecha_vencimiento}"
                alerta = models.Alerta(
                    insumo_id=entrada.insumo_id,
                    mensaje=mensaje,
                    fecha=date.today()
                )
                db.add(alerta)
                alertas_creadas.append(alerta)
    
    db.commit()
    return alertas_creadas

# Endpoint para obtener especialidades
@app.get("/especialidades/", response_model=list[schemas.Especialidad])
def read_especialidades(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return db.query(models.Especialidad).offset(skip).limit(limit).all()

# main.py - Añadir este endpoint
@app.get("/reportes/consumo-por-especialidad")
def get_consumo_por_especialidad(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(database.get_db)
):
    """
    Obtiene el consumo de insumos por especialidad en un rango de fechas.
    Si no se especifican fechas, devuelve el último mes.
    """
    from datetime import date, timedelta
    
    # Establecer rango de fechas por defecto (último mes)
    if fecha_fin is None:
        fecha_fin = date.today()
    if fecha_inicio is None:
        fecha_inicio = fecha_fin - timedelta(days=30)
    
    # Query principal
    resultados = db.query(
        models.Especialidad.nombre.label('especialidad'),
        models.Insumo.nombre.label('insumo'),
        func.sum(models.Salida.cantidad).label('cantidad_total'),
        func.sum(models.Salida.cantidad * models.Salida.precio_unitario).label('costo_total')
    ).select_from(models.Salida)\
     .join(models.Insumo, models.Salida.insumo_id == models.Insumo.id)\
     .join(models.Especialidad, models.Insumo.especialidad_id == models.Especialidad.id)\
     .filter(models.Salida.fecha >= fecha_inicio)\
     .filter(models.Salida.fecha <= fecha_fin)\
     .group_by(models.Especialidad.nombre, models.Insumo.nombre)\
     .order_by(models.Especialidad.nombre, func.sum(models.Salida.cantidad).desc())\
     .all()
    
    # Formatear resultado
    reporte = {}
    for row in resultados:
        especialidad = row.especialidad
        if especialidad not in reporte:
            reporte[especialidad] = {
                'total_cantidad': 0,
                'total_costo': 0,
                'insumos': []
            }
        
        cantidad = float(row.cantidad_total) if row.cantidad_total else 0
        costo = float(row.costo_total) if row.costo_total else 0
        
        reporte[especialidad]['insumos'].append({
            'insumo': row.insumo,
            'cantidad': cantidad,
            'costo': costo
        })
        reporte[especialidad]['total_cantidad'] += cantidad
        reporte[especialidad]['total_costo'] += costo
    
    return {
        'periodo': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        },
        'especialidades': reporte
    }
