# ============================================================
# GUÍA DE DESPLIEGUE EN PYTHONANYWHERE
# MENÚ DIGITAL SAAS - DIVERGENT STUDIO
# ============================================================

## 📊 PLANES DE PYTHONANYWHERE RECOMENDADOS

Para 300 clientes, cada uno con su restaurante:

| Plan | Precio | Workers | Almacenamiento | Recomendación |
|------|--------|---------|----------------|---------------|
| **Hacker** | $5/mes | 1 worker | 512MB | ❌ Muy limitado para 300 clientes |
| **Web Dev** | $12/mes | 2 workers | 1GB | ⚠️ Mínimo aceptable |
| **Startup** | $99/mes | 10 workers | 10GB | ✅ **RECOMENDADO** para 300 clientes |
| **Business** | $199/mes | 20 workers | 20GB | 🚀 Para escalar a más clientes |

### ¿Por qué Startup ($99/mes)?

- **300 restaurantes × 10 visitas/día = 3,000 requests/día**
- **Picos de almuerzo/cena**: Necesitas múltiples workers
- **Base de datos SQLite**: OK para empezar, pero considera MySQL en el futuro
- **SSL incluido**: HTTPS gratis (importante para profesionalismo)

---

## 🚀 PASOS PARA DESPLEGAR

### 1. Crear cuenta en PythonAnywhere
- Ve a https://www.pythonanywhere.com
- Elige el plan **Startup** o superior

### 2. Subir archivos
```bash
# En la consola Bash de PythonAnywhere:
cd ~
git clone TU_REPOSITORIO mimenúdigital

# O sube los archivos manualmente via Files
```

### 3. Instalar dependencias
```bash
pip install --user flask werkzeug
```

### 4. Configurar la Web App
1. Ve a la pestaña **Web**
2. Click en **Add a new web app**
3. Elige **Manual configuration** → **Python 3.10+**
4. Configura:
   - **Source code**: `/home/TU_USUARIO/mimenúdigital`
   - **Working directory**: `/home/TU_USUARIO/mimenúdigital`

### 5. Editar archivo WSGI
En la sección "Code", haz click en el link del archivo WSGI y reemplaza todo con:

```python
import sys
import os

project_home = '/home/TU_USUARIO/mimenúdigital'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'GENERA_UNA_CLAVE_SEGURA_AQUI'
os.environ['BASE_URL'] = 'https://TU_USUARIO.pythonanywhere.com'
os.environ['DATABASE_PATH'] = '/home/TU_USUARIO/mimenúdigital/menu_digital.db'

from app_menu import app as application
```

### 6. Reload la aplicación
Click en el botón verde **Reload**

---

## 🔒 CONFIGURACIÓN DE DOMINIO PERSONALIZADO

Para usar un dominio como `menu.tuempresa.com`:

1. En PythonAnywhere → Web → "Web app domain"
2. Añade tu dominio personalizado
3. En tu proveedor de dominio, configura un CNAME:
   ```
   menu.tuempresa.com  →  CNAME  →  TU_USUARIO.pythonanywhere.com
   ```
4. Actualiza `BASE_URL` en el archivo WSGI

---

## 📈 CÓMO FUNCIONA PARA CADA CLIENTE

### Flujo del cliente (dueño de restaurante):

1. **Tú creas su cuenta** desde el panel SuperAdmin
   - Usuario: `restaurante-nombre`
   - Contraseña: generada
   - Restaurante: con su URL única

2. **El cliente recibe sus credenciales**:
   - Login: `https://TU_DOMINIO/login`
   - Usuario: `juanito`
   - Contraseña: `password123`

3. **El cliente accede a SU panel**:
   - Ve SOLO su restaurante
   - Gestiona SUS platos y categorías
   - Ve SUS estadísticas de visitas/QR
   - Descarga SU código QR

4. **Los comensales del restaurante**:
   - Escanean el QR
   - Ven el menú en: `https://TU_DOMINIO/menu/nombre-restaurante`
   - Cada visita se registra en las estadísticas

---

## 💰 MODELO DE NEGOCIO SUGERIDO

| Plan Cliente | Precio Sugerido | Incluye |
|--------------|-----------------|---------|
| **Básico** | $10.000/mes | 1 menú, 50 platos, stats básicos |
| **Pro** | $25.000/mes | 1 menú, platos ilimitados, stats completos |
| **Premium** | $50.000/mes | Dominio personalizado, soporte prioritario |

### Con 300 clientes en plan Básico:
- Ingresos: 300 × $10.000 = **$3.000.000 CLP/mes**
- Costo PythonAnywhere: ~$99 USD (~$90.000 CLP)
- **Margen: ~97%** 🎉

---

## 🔧 MANTENIMIENTO

### Backups (IMPORTANTE)
```bash
# Ejecutar diariamente via Scheduled Tasks
cp /home/TU_USUARIO/mimenúdigital/menu_digital.db /home/TU_USUARIO/backups/menu_digital_$(date +%Y%m%d).db
```

### Monitoreo
- PythonAnywhere muestra logs de errores
- Revisa `/var/log/TU_USUARIO.pythonanywhere.com.error.log`

### Escalamiento futuro
Cuando superes 500+ clientes, considera:
1. Migrar a MySQL (incluido en planes pagos)
2. Usar AWS/DigitalOcean para más control
3. Implementar caché con Redis

---

## 📋 CHECKLIST ANTES DE LANZAR

- [ ] Cambiar SECRET_KEY por una clave segura
- [ ] Actualizar BASE_URL con tu dominio real
- [ ] Probar el login como SuperAdmin
- [ ] Crear un restaurante de prueba
- [ ] Probar el menú público desde móvil
- [ ] Verificar que el tracking de visitas funciona
- [ ] Configurar backups automáticos
- [ ] Comprar dominio profesional (opcional pero recomendado)

---

¡Éxito con tu negocio! 🍕🚀
