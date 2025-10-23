# crud.py
from sqlalchemy.orm import Session
import models
import schemas
from utils import get_password_hash

def get_usuario_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def create_usuario(db: Session, usuario: schemas.UsuarioCreate):
    hashed_password = get_password_hash(usuario.password)
    db_usuario = models.Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password_hash=hashed_password,
        rol=usuario.rol
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def get_insumos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Insumo).offset(skip).limit(limit).all()

def create_insumo(db: Session, insumo: schemas.InsumoCreate):
    db_insumo = models.Insumo(**insumo.dict())
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo

def get_insumo(db: Session, insumo_id: int):
    return db.query(models.Insumo).filter(models.Insumo.id == insumo_id).first()

def update_insumo(db: Session, insumo_id: int, insumo: schemas.InsumoCreate):
    db_insumo = get_insumo(db, insumo_id)
    if db_insumo:
        for key, value in insumo.dict().items():
            setattr(db_insumo, key, value)
        db.commit()
        db.refresh(db_insumo)
    return db_insumo

def delete_insumo(db: Session, insumo_id: int):
    db_insumo = get_insumo(db, insumo_id)
    if db_insumo:
        db.delete(db_insumo)
        db.commit()
    return db_insumo

def create_entrada(db: Session, entrada: schemas.EntradaCreate):
    db_entrada = models.Entrada(**entrada.dict())
    db.add(db_entrada)
    db.commit()
    db.refresh(db_entrada)
    return db_entrada

def get_entradas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Entrada).offset(skip).limit(limit).all()

def create_salida(db: Session, salida: schemas.SalidaCreate):
    db_salida = models.Salida(**salida.dict())
    db.add(db_salida)
    db.commit()
    db.refresh(db_salida)
    return db_salida

def get_salidas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Salida).offset(skip).limit(limit).all()

def create_alerta(db: Session, alerta: schemas.AlertaCreate):
    db_alerta = models.Alerta(**alerta.dict())
    db.add(db_alerta)
    db.commit()
    db.refresh(db_alerta)
    return db_alerta

def get_alertas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Alerta).offset(skip).limit(limit).all()