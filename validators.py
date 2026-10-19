# ============================================================
# VALIDADORES - Funciones de validación reutilizables
# Menú Digital SaaS - Divergent Studio
# ============================================================

import re
from functools import wraps


def validar_email(email):
    """
    Valida formato de email.
    
    Args:
        email: String con el email a validar
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str o None)
    """
    if not email:
        return False, "El email es requerido"
    
    email = email.strip().lower()
    
    if len(email) > 254:
        return False, "El email es demasiado largo"
    
    # Regex para validación de email (RFC 5322 simplificado)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Formato de email inválido"
    
    return True, None


def validar_password(password, min_length=8, require_complexity=True):
    """
    Valida seguridad de contraseña.
    
    Args:
        password: String con la contraseña
        min_length: Longitud mínima (default 8)
        require_complexity: Si requiere mayúsculas, números, etc.
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str o None)
    """
    if not password:
        return False, "La contraseña es requerida"
    
    if len(password) < min_length:
        return False, f"La contraseña debe tener al menos {min_length} caracteres"
    
    if len(password) > 128:
        return False, "La contraseña es demasiado larga"
    
    if require_complexity:
        errors = []
        
        if not re.search(r'[A-Z]', password):
            errors.append("una mayúscula")
        
        if not re.search(r'[a-z]', password):
            errors.append("una minúscula")
        
        if not re.search(r'\d', password):
            errors.append("un número")
        
        if errors:
            return False, f"La contraseña debe contener al menos: {', '.join(errors)}"
    
    # Verificar contraseñas comunes
    common_passwords = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'password123', 'admin123', '123456789', 'letmein', 'welcome'
    ]
    
    if password.lower() in common_passwords:
        return False, "Esta contraseña es muy común, elige una más segura"
    
    return True, None


def validar_url_slug(slug):
    """
    Valida formato de URL slug.
    
    Args:
        slug: String con el slug a validar
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str o None)
    """
    if not slug:
        return False, "El slug es requerido"
    
    slug = slug.strip().lower()
    
    if len(slug) < 3:
        return False, "El slug debe tener al menos 3 caracteres"
    
    if len(slug) > 100:
        return False, "El slug es demasiado largo"
    
    # Solo letras minúsculas, números y guiones
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    
    if not re.match(pattern, slug):
        return False, "El slug solo puede contener letras minúsculas, números y guiones (no al inicio/fin)"
    
    # Slugs reservados
    reserved = [
        'admin', 'api', 'static', 'login', 'logout', 'register', 
        'superadmin', 'gestion', 'soporte', 'pago', 'webhook',
        'menu', 'dashboard', 'healthz', 'health'
    ]
    
    if slug in reserved:
        return False, "Este slug está reservado, elige otro"
    
    return True, None


def validar_telefono(telefono, pais='CL'):
    """
    Valida formato de teléfono.
    
    Args:
        telefono: String con el teléfono
        pais: Código de país (default Chile)
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str o None)
    """
    if not telefono:
        return True, None  # Opcional
    
    # Limpiar caracteres no numéricos
    telefono_limpio = re.sub(r'[^\d+]', '', telefono)
    
    if pais == 'CL':
        # Chile: +56 9 XXXX XXXX o 9 XXXX XXXX
        if telefono_limpio.startswith('+56'):
            telefono_limpio = telefono_limpio[3:]
        
        if len(telefono_limpio) < 9 or len(telefono_limpio) > 11:
            return False, "Número de teléfono inválido para Chile"
    
    return True, None


def validar_rut(rut):
    """
    Valida RUT chileno.
    
    Args:
        rut: String con el RUT (con o sin formato)
        
    Returns:
        tuple: (es_valido: bool, mensaje_error: str o None)
    """
    if not rut:
        return True, None  # Opcional
    
    # Limpiar RUT
    rut = rut.upper().replace('.', '').replace('-', '').replace(' ', '')
    
    if len(rut) < 8 or len(rut) > 9:
        return False, "RUT inválido"
    
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    if not cuerpo.isdigit():
        return False, "RUT inválido"
    
    # Calcular dígito verificador
    suma = 0
    multiplo = 2
    
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        dv_esperado = '0'
    elif dv_calculado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_calculado)
    
    if dv != dv_esperado:
        return False, "RUT inválido (dígito verificador incorrecto)"
    
    return True, None


def sanitizar_html(texto):
    """
    Elimina tags HTML potencialmente peligrosos.
    
    Args:
        texto: String a sanitizar
        
    Returns:
        String sanitizado
    """
    if not texto:
        return ''
    
    # Eliminar tags de script y style
    texto = re.sub(r'<script[^>]*>.*?</script>', '', texto, flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r'<style[^>]*>.*?</style>', '', texto, flags=re.IGNORECASE | re.DOTALL)
    
    # Eliminar event handlers
    texto = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', texto, flags=re.IGNORECASE)
    
    # Eliminar javascript: URLs
    texto = re.sub(r'javascript:', '', texto, flags=re.IGNORECASE)
    
    return texto.strip()


def sanitizar_nombre(nombre):
    """
    Sanitiza nombres (personas, restaurantes, etc.).
    
    Args:
        nombre: String con el nombre
        
    Returns:
        String sanitizado
    """
    if not nombre:
        return ''
    
    # Eliminar HTML
    nombre = re.sub(r'<[^>]+>', '', nombre)
    
    # Eliminar caracteres especiales peligrosos
    nombre = re.sub(r'[<>"\';\\]', '', nombre)
    
    # Normalizar espacios
    nombre = ' '.join(nombre.split())
    
    return nombre.strip()


class ValidationError(Exception):
    """Excepción para errores de validación."""
    
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_request_data(schema):
    """
    Decorador para validar datos de request JSON según un schema.
    
    Args:
        schema: Dict con el schema de validación
                {
                    'campo': {
                        'required': bool,
                        'type': str/int/float/bool/list,
                        'min_length': int (para strings),
                        'max_length': int (para strings),
                        'min': number (para números),
                        'max': number (para números),
                        'validator': callable(valor) -> (bool, str)
                    }
                }
    
    Returns:
        Decorador que valida el request antes de ejecutar la función
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
            
            errors = []
            
            for field, rules in schema.items():
                value = data.get(field)
                
                # Campo requerido
                if rules.get('required', False) and (value is None or value == ''):
                    errors.append(f"El campo '{field}' es requerido")
                    continue
                
                # Si no hay valor y no es requerido, saltar validación
                if value is None or value == '':
                    continue
                
                # Tipo de dato
                expected_type = rules.get('type')
                if expected_type:
                    if expected_type == str and not isinstance(value, str):
                        errors.append(f"El campo '{field}' debe ser texto")
                    elif expected_type == int and not isinstance(value, int):
                        errors.append(f"El campo '{field}' debe ser un número entero")
                    elif expected_type == float and not isinstance(value, (int, float)):
                        errors.append(f"El campo '{field}' debe ser un número")
                    elif expected_type == bool and not isinstance(value, bool):
                        errors.append(f"El campo '{field}' debe ser verdadero/falso")
                    elif expected_type == list and not isinstance(value, list):
                        errors.append(f"El campo '{field}' debe ser una lista")
                
                # Longitud mínima (strings)
                min_length = rules.get('min_length')
                if min_length and isinstance(value, str) and len(value) < min_length:
                    errors.append(f"El campo '{field}' debe tener al menos {min_length} caracteres")
                
                # Longitud máxima (strings)
                max_length = rules.get('max_length')
                if max_length and isinstance(value, str) and len(value) > max_length:
                    errors.append(f"El campo '{field}' no puede exceder {max_length} caracteres")
                
                # Valor mínimo (números)
                min_val = rules.get('min')
                if min_val is not None and isinstance(value, (int, float)) and value < min_val:
                    errors.append(f"El campo '{field}' debe ser al menos {min_val}")
                
                # Valor máximo (números)
                max_val = rules.get('max')
                if max_val is not None and isinstance(value, (int, float)) and value > max_val:
                    errors.append(f"El campo '{field}' no puede exceder {max_val}")
                
                # Validador personalizado
                validator = rules.get('validator')
                if validator and callable(validator):
                    is_valid, error_msg = validator(value)
                    if not is_valid:
                        errors.append(f"{field}: {error_msg}")
            
            if errors:
                return jsonify({
                    'success': False, 
                    'error': 'Errores de validación',
                    'errors': errors
                }), 400
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator
