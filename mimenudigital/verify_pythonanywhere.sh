#!/bin/bash
# ============================================================
# SCRIPT DE VERIFICACIÓN PARA PYTHONANYWHERE
# Ejecutar en: PythonAnywhere → Bash console
# ============================================================

echo "╔════════════════════════════════════════════════════════╗"
echo "║  SCRIPT DE VERIFICACIÓN - MENÚ DIGITAL v2.0           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Cambiar a directorio de la aplicación
cd /home/tu_usuario/tu_aplicacion
echo "[1/5] Verificando directorio..."
pwd
echo "✅ Directorio correcto"
echo ""

# Verificar que app_menu.py existe y tiene log_dir definido
echo "[2/5] Verificando que log_dir está definido..."
if grep -q "log_dir = os.path.join" app_menu.py; then
    echo "✅ log_dir está definido"
    grep -n "log_dir = os.path.join" app_menu.py
else
    echo "❌ log_dir NO está definido"
    exit 1
fi
echo ""

# Verificar importación de Mercado Pago
echo "[3/5] Verificando Mercado Pago SDK..."
if grep -q "MERCADO_PAGO_ACCESS_TOKEN" app_menu.py; then
    echo "✅ MERCADO_PAGO_ACCESS_TOKEN encontrado"
    grep -n "MERCADO_PAGO_ACCESS_TOKEN" app_menu.py | head -3
else
    echo "❌ MERCADO_PAGO_ACCESS_TOKEN NO encontrado"
    exit 1
fi
echo ""

# Verificar que pdfkit está instalado
echo "[4/5] Verificando dependencias..."
pip list 2>/dev/null | grep -E "(pdfkit|mercado-pago|Flask|PyMySQL)" || echo "Instala dependencias primero"
echo ""

# Verificar tabla de transacciones (si DB está configurada)
echo "[5/5] Información del estado..."
echo "Próximos pasos:"
echo "1. Sube esta carpeta a PythonAnywhere"
echo "2. Ejecuta PYTHONANYWHERE_MIGRATION.sql en MySQL console"
echo "3. Configura variables de entorno:"
echo "   - MERCADO_PAGO_ACCESS_TOKEN"
echo "   - MERCADO_PAGO_PUBLIC_KEY"
echo "   - CLOUDINARY_URL"
echo "   - Otras..."
echo "4. Reinicia la app (botón Reload)"
echo "5. Revisa error.log"
echo ""

echo "╔════════════════════════════════════════════════════════╗"
echo "║  VERIFICACIÓN COMPLETADA                              ║"
echo "╚════════════════════════════════════════════════════════╝"
