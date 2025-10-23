# schemas.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class UsuarioBase(BaseModel):
    nombre: str
    email: str
    rol: str

class UsuarioCreate(UsuarioBase):
    password: str

class Usuario(UsuarioBase):
    id: int
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ✅ Esquema para Especialidad
class EspecialidadBase(BaseModel):
    nombre: str

class EspecialidadCreate(EspecialidadBase):
    pass

class Especialidad(EspecialidadBase):
    id: int
    
    class Config:
        from_attributes = True

# ✅ Esquema para Insumo - INCLUYE especialidad
class InsumoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    unidad_medida: Optional[str] = None
    stock_minimo: float = 0.0
    especialidad_id: Optional[int] = None

class InsumoCreate(InsumoBase):
    pass

class Insumo(InsumoBase):
    id: int
    stock_actual: float = 0.0
    # ✅ Incluir la especialidad como campo anidado
    especialidad: Optional[Especialidad] = None
    
    class Config:
        from_attributes = True

# Resto de tus esquemas (Entrada, Salida, Alerta, etc.)
class EntradaBase(BaseModel):
    insumo_id: int
    cantidad: float
    precio_unitario: Optional[float] = 0.0
    fecha: date
    usuario_id: Optional[int] = None
    numero_referencia: Optional[str] = None
    remitente_destinatario: Optional[str] = None
    numero_lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None

class EntradaCreate(EntradaBase):
    pass

class Entrada(EntradaBase):
    id: int
    
    class Config:
        from_attributes = True

class SalidaBase(BaseModel):
    insumo_id: int
    cantidad: float
    precio_unitario: Optional[float] = 0.0
    fecha: date
    usuario_id: Optional[int] = None
    numero_referencia: Optional[str] = None
    remitente_destinatario: Optional[str] = None
    numero_lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None

class SalidaCreate(SalidaBase):
    pass

class Salida(SalidaBase):
    id: int
    
    class Config:
        from_attributes = True

class AlertaBase(BaseModel):
    insumo_id: int
    mensaje: str
    fecha: date

class AlertaCreate(AlertaBase):
    pass

class Alerta(AlertaBase):
    id: int
    
    class Config:
        from_attributes = True