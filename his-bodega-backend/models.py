# models.py
from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, Enum, ForeignKey, DATE, DATETIME
from sqlalchemy.orm import relationship  # ✅ IMPORTANTE: esta línea faltaba
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum('admin', 'empleado'), default='empleado')
    created_at = Column(TIMESTAMP, server_default=func.now())

class Especialidad(Base):  # ✅ NUEVA TABLA
    __tablename__ = "especialidades"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Insumo(Base):
    __tablename__ = "insumos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    unidad_medida = Column(String(50))
    stock_actual = Column(DECIMAL(10,2), default=0.00)
    stock_minimo = Column(DECIMAL(10,2), default=0.00)
    especialidad_id = Column(Integer, ForeignKey("especialidades.id"))  # ✅ NUEVO CAMPO
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relación con especialidad
    especialidad = relationship("Especialidad")  # ✅ Ahora sí está definido

class Entrada(Base):
    __tablename__ = "entradas"
    id = Column(Integer, primary_key=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(DECIMAL(10,2), nullable=False)
    precio_unitario = Column(DECIMAL(10,2), default=0.00)
    fecha = Column(DATE, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    numero_referencia = Column(String(100))
    remitente_destinatario = Column(String(255))
    numero_lote = Column(String(100))
    fecha_vencimiento = Column(DATE)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Salida(Base):
    __tablename__ = "salidas"
    id = Column(Integer, primary_key=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(DECIMAL(10,2), nullable=False)
    precio_unitario = Column(DECIMAL(10,2), default=0.00)
    fecha = Column(DATE, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    numero_referencia = Column(String(100))
    remitente_destinatario = Column(String(255))
    numero_lote = Column(String(100))
    fecha_vencimiento = Column(DATE)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Alerta(Base):
    __tablename__ = "alertas"
    id = Column(Integer, primary_key=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    mensaje = Column(Text, nullable=False)
    fecha = Column(DATE, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Auditoria(Base):
    __tablename__ = "auditoria"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    accion = Column(String(255), nullable=False)
    detalle = Column(Text)
    fecha = Column(DATETIME, server_default=func.now())
    ip_address = Column(String(45))