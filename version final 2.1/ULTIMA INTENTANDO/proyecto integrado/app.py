from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session, Response, g
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash

from config import config
from database import init_database, get_db, close_db

app = Flask(__name__)
# Selecciona la configuración a usar, con 'default' como opción predeterminada.
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

# Crear directorios
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Llama a la función de inicialización de la base de datos
init_database()


# ===== DECORADOR PARA RUTAS PROTEGIDAS =====
def login_required(f):
    """Decorador para requerir autenticación"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== RUTAS DE AUTENTICACIÓN =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    # Si ya está logueado, redirigir al dashboard
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        # Buscar usuario
        user = db.execute('SELECT id, username, password_hash, nombre, rol FROM usuarios WHERE username = ? AND activo = 1', (username,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            # Login exitoso
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nombre'] = user['nombre']
            session['rol'] = user['rol']
            flash('¡Bienvenido ' + user['nombre'] + '!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('login'))

@app.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    """Cambiar contraseña"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Las contraseñas nuevas no coinciden', 'error')
            return render_template('cambiar_password.html')
        
        db = get_db()
        
        # Verificar contraseña actual
        user = db.execute('SELECT password_hash FROM usuarios WHERE id = ?', (session['user_id'],)).fetchone()
        
        if user and check_password_hash(user['password_hash'], current_password):
            # Actualizar contraseña
            new_password_hash = generate_password_hash(new_password)
            db.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (new_password_hash, session['user_id']))
            db.commit()
            flash('Contraseña actualizada exitosamente', 'success')
            return redirect(url_for('index'))
        else:
            flash('Contraseña actual incorrecta', 'error')
    
    return render_template('cambiar_password.html')

# ===== RUTAS PRINCIPALES PROTEGIDAS =====

@app.route('/')
@login_required
def index():
    """Dashboard principal"""
    db = get_db()
    
    stats = {
        'total_clientes': db.execute("SELECT COUNT(*) FROM clientes WHERE activo = 1").fetchone()[0],
        'total_proyectos': db.execute("SELECT COUNT(*) FROM proyectos WHERE estado = 'Activo'").fetchone()[0],
        'facturas_pendientes': db.execute("SELECT COUNT(*) FROM facturas WHERE estado = 'Pendiente'").fetchone()[0],
        'deuda_total': db.execute("SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE estado = 'Pendiente'").fetchone()[0]
    }
    
    facturas_recientes = db.execute(
        "SELECT d.*, c.razon_social FROM facturas d LEFT JOIN clientes c ON d.cliente_rut = c.rut ORDER BY d.fecha_emision DESC LIMIT 5"
    ).fetchall()
    
    clientes = db.execute("SELECT rut, razon_social FROM clientes WHERE activo = 1 ORDER BY razon_social").fetchall()
    
    return render_template('index.html', stats=stats, facturas=facturas_recientes, clientes=clientes)

@app.route('/clientes')
@login_required
def clientes():
    """Gestión de clientes"""
    db = get_db()
    clientes_list = db.execute("SELECT * FROM clientes WHERE activo = 1 ORDER BY razon_social").fetchall()
    return render_template('clientes.html', clientes=clientes_list)

@app.route('/proyectos')
@login_required
def proyectos():
    """Gestión de proyectos"""
    db = get_db()
    
    proyectos_rows = db.execute('''
        SELECT p.*, c.razon_social 
        FROM proyectos p 
        LEFT JOIN clientes c ON p.cliente_rut = c.rut 
        WHERE p.estado != 'Inactivo'
        ORDER BY p.estado, p.fecha_inicio DESC
    ''').fetchall()
    proyectos_list = [dict(row) for row in proyectos_rows]
    
    clientes_rows = db.execute("SELECT rut, razon_social FROM clientes WHERE activo = 1 ORDER BY razon_social").fetchall()
    clientes_list = [dict(row) for row in clientes_rows]
    
    return render_template('proyectos.html', proyectos=proyectos_list, clientes=clientes_list)

import json

#...

@app.route('/facturas')
@login_required
def facturas():
    """Generación y Gestión de facturas"""
    db = get_db()
    clientes = db.execute("SELECT rut, razon_social, giro, direccion, comuna FROM clientes WHERE activo = 1").fetchall()
    clientes_json = json.dumps([dict(ix) for ix in clientes])
    proyectos = db.execute("SELECT codigo, nombre FROM proyectos WHERE estado = 'Activo'").fetchall()
    
    ultima_factura = get_ultimo_numero_factura('FAC')

    facturas_facturas_rows = db.execute('''
        SELECT 
            d.*, 
            c.razon_social, 
            p.nombre as proyecto_nombre 
        FROM facturas d
        LEFT JOIN clientes c ON d.cliente_rut = c.rut
        LEFT JOIN proyectos p ON d.proyecto_codigo = p.codigo
        WHERE d.tipo_doc = 'FAC'
        ORDER BY d.fecha_emision DESC
    ''').fetchall()
    facturas_facturas = [dict(row) for row in facturas_facturas_rows]
    
    return render_template('facturas.html', 
                         clientes=clientes, 
                         clientes_json=clientes_json,
                         proyectos=proyectos,
                         proximo_numero=ultima_factura + 1,
                         facturas_facturas=facturas_facturas)

@app.route('/boletas')
@login_required
def boletas():
    """Generación de boletas"""
    db = get_db()
    clientes = db.execute("SELECT rut, razon_social FROM clientes WHERE activo = 1").fetchall()
    proyectos = db.execute("SELECT codigo, nombre FROM proyectos WHERE estado = 'Activo'").fetchall()
    
    ultima_boleta = get_ultimo_numero_factura('BOL')
    
    return render_template('boletas.html', 
                         clientes=clientes, 
                         proyectos=proyectos,
                         proximo_numero=ultima_boleta + 1)

@app.route('/notas-credito')
@login_required
def notas_credito():
    """Generación de notas de crédito"""
    db = get_db()
    clientes = db.execute("SELECT rut, razon_social FROM clientes WHERE activo = 1").fetchall()
    motivos = db.execute("SELECT * FROM motivos_nc_nd WHERE tipo = 'NC' AND activo = 1").fetchall()
    
    facturas_referencia = db.execute('''
        SELECT d.id, d.numero_doc, d.tipo_doc, d.valor_total, c.razon_social, d.fecha_emision
        FROM facturas d 
        LEFT JOIN clientes c ON d.cliente_rut = c.rut 
        WHERE d.tipo_doc IN ('FAC', 'BOL') AND d.estado != 'Anulado'
        ORDER BY d.fecha_emision DESC
    ''').fetchall()
    
    ultima_nc = get_ultimo_numero_factura('NC')
    
    return render_template('notas_credito.html', 
                         clientes=clientes,
                         motivos=motivos,
                         facturas_referencia=facturas_referencia,
                         proximo_numero=ultima_nc + 1)

@app.route('/notas-debito')
@login_required
def notas_debito():
    """Generación de notas de débito"""
    db = get_db()
    clientes = db.execute("SELECT rut, razon_social FROM clientes WHERE activo = 1").fetchall()
    motivos = db.execute("SELECT * FROM motivos_nc_nd WHERE tipo = 'ND' AND activo = 1").fetchall()
    
    facturas_referencia = db.execute('''
        SELECT d.id, d.numero_doc, d.tipo_doc, d.valor_total, c.razon_social, d.fecha_emision
        FROM facturas d 
        LEFT JOIN clientes c ON d.cliente_rut = c.rut 
        WHERE d.tipo_doc IN ('FAC', 'BOL') AND d.estado != 'Anulado'
        ORDER BY d.fecha_emision DESC
    ''').fetchall()
    
    ultima_nd = get_ultimo_numero_factura('ND')
    
    return render_template('notas_debito.html', 
                         clientes=clientes,
                         motivos=motivos,
                         facturas_referencia=facturas_referencia,
                         proximo_numero=ultima_nd + 1)

@app.route('/reportes')
@login_required
def reportes():
    """Página de reportes"""
    return render_template('reportes.html')

# ===== APIs PROTEGIDAS =====

@app.route('/api/generar-documento', methods=['POST'])
@login_required
def api_generar_factura():
    """API para generar facturas"""
    data = request.get_json()
    db = get_db()
    
    try:
        cursor = db.cursor()
        
        # --- Lógica para el Folio ---
        folio = None
        if data.get('folio_automatico'):
            ultimo_folio = get_ultimo_numero_factura(data['tipo_doc'])
            folio = ultimo_folio + 1
        else:
            folio = data.get('folio_manual')

        if not folio:
            return jsonify({'success': False, 'error': 'El número de folio no puede estar vacío.'})
        # --- Fin Lógica para el Folio ---

        cursor.execute('''
            INSERT INTO facturas 
            (numero_doc, tipo_doc, folio, fecha_emision, fecha_vencimiento, 
             cliente_rut, proyecto_codigo, descripcion, valor_neto, iva, valor_total, 
             estado, forma_pago, observaciones, factura_referencia_id, motivo_nc_nd, usuario_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            folio,
            data['tipo_doc'],
            folio,
            data['fecha_emision'],
            data.get('fecha_vencimiento'),
            data['cliente_rut'],
            data.get('proyecto_codigo'),
            data['descripcion'],
            data['valor_neto'],
            data['iva'],
            data['valor_total'],
            data.get('estado', 'Pendiente'),
            data.get('forma_pago', 'Contado'),
            data.get('observaciones', ''),
            data.get('factura_referencia_id'),
            data.get('motivo_nc_nd'),
            session['username']
        ))
        
        factura_id = cursor.lastrowid
        
        for item in data.get('items', []):
            cursor.execute('''
                INSERT INTO factura_items 
                (factura_id, codigo_producto, descripcion, cantidad, precio_unitario, descuento, total_linea)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                factura_id,
                item.get('codigo', ''),
                item['descripcion'],
                item['cantidad'],
                item['precio_unitario'],
                item.get('descuento', 0),
                item['total_linea']
            ))
        
        db.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{data["tipo_doc"]} generada exitosamente con el folio {folio}',
            'factura_id': factura_id
        })
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ===== APIs CRUD PARA CLIENTES Y PROYECTOS =====

@app.route('/api/clientes', methods=['GET', 'POST', 'DELETE', 'PUT'])
@login_required
def api_clientes():
    """API para gestión de clientes"""
    db = get_db()
    
    if request.method == 'GET':
        clientes = db.execute("SELECT * FROM clientes WHERE activo = 1").fetchall()
        return jsonify(clientes)
    
    elif request.method == 'POST':
        data = request.get_json()
        try:
            cursor = db.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO clientes 
                (rut, razon_social, giro, direccion, comuna, telefono, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['rut'],
                data['razon_social'],
                data.get('giro', ''),
                data.get('direccion', ''),
                data.get('comuna', ''),
                data.get('telefono', ''),
                data.get('email', '')
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Cliente guardado exitosamente'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'PUT':
        rut = request.args.get('rut')
        data = request.get_json()
        try:
            cursor = db.cursor()
            cursor.execute('''
                UPDATE clientes SET
                    razon_social = ?,
                    giro = ?,
                    direccion = ?,
                    comuna = ?,
                    telefono = ?,
                    email = ?
                WHERE rut = ?
            ''', (
                data['razon_social'],
                data.get('giro', ''),
                data.get('direccion', ''),
                data.get('comuna', ''),
                data.get('telefono', ''),
                data.get('email', ''),
                rut
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Cliente actualizado exitosamente'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    elif request.method == 'DELETE':
        rut = request.args.get('rut')
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE clientes SET activo = 0 WHERE rut = ?", (rut,))
            db.commit()
            return jsonify({'success': True, 'message': 'Cliente eliminado'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/proyectos', methods=['GET', 'POST'])
@login_required
def api_proyectos():
    """API para gestión de proyectos - CORREGIDO CON CÓDIGO AUTOMÁTICO"""
    db = get_db()
    
    if request.method == 'GET':
        proyectos = db.execute('''
            SELECT p.*, c.razon_social 
            FROM proyectos p 
            LEFT JOIN clientes c ON p.cliente_rut = c.rut
        ''').fetchall()
        return jsonify(proyectos)
    
    elif request.method == 'POST':
        data = request.get_json()
        try:
            cursor = db.cursor()
            
            # GENERAR CÓDIGO AUTOMÁTICO
            ultimo_proyecto_row = cursor.execute("SELECT MAX(id) FROM proyectos").fetchone()
            ultimo_proyecto = ultimo_proyecto_row[0] if ultimo_proyecto_row else 0
            codigo_auto = f"PROY-{(ultimo_proyecto or 0) + 1:04d}"
            
            # VERIFICAR SI EL CLIENTE EXISTE
            if data.get('cliente_rut'):
                cliente_existe_row = cursor.execute("SELECT COUNT(*) FROM clientes WHERE rut = ?", (data['cliente_rut'],)).fetchone()
                cliente_existe = cliente_existe_row[0]
                
                if cliente_existe == 0:
                    return jsonify({'success': False, 'error': 'El cliente seleccionado no existe'})
            
            # INSERTAR NUEVO PROYECTO
            cursor.execute('''
                INSERT INTO proyectos 
                (codigo, nombre, descripcion, cliente_rut, fecha_inicio, fecha_termino, presupuesto, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                codigo_auto,  # Código automático
                data['nombre'],
                data['descripcion'],
                data.get('cliente_rut'),  # Puede ser None
                data['fecha_inicio'],
                data.get('fecha_termino'),
                data.get('presupuesto', 0),
                data.get('estado', 'Activo')
            ))
            db.commit()
            return jsonify({'success': True, 'message': f'Proyecto {codigo_auto} guardado exitosamente'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/proyectos/<string:codigo>', methods=['PUT', 'DELETE'])
@login_required
def api_proyecto_detalle(codigo):
    """API para actualizar o eliminar un proyecto específico."""
    db = get_db()

    if request.method == 'PUT':
        data = request.get_json()
        try:
            cursor = db.cursor()
            cursor.execute('''
                UPDATE proyectos SET
                    nombre = ?,
                    descripcion = ?,
                    cliente_rut = ?,
                    fecha_inicio = ?,
                    fecha_termino = ?,
                    presupuesto = ?,
                    estado = ?
                WHERE codigo = ?
            ''', (
                data['nombre'],
                data.get('descripcion', ''),
                data.get('cliente_rut'),
                data['fecha_inicio'],
                data.get('fecha_termino'),
                data.get('presupuesto', 0),
                data.get('estado', 'Activo'),
                codigo
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Proyecto actualizado exitosamente'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'DELETE':
        try:
            cursor = db.cursor()
            # Desactivar en lugar de borrar para mantener el historial
            cursor.execute("UPDATE proyectos SET estado = 'Inactivo' WHERE codigo = ?", (codigo,))
            db.commit()
            return jsonify({'success': True, 'message': 'Proyecto desactivado exitosamente'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})

# ===== SISTEMA DE REPORTES COMPLETO =====

@app.route('/api/reporte-deudas')
@login_required
def api_reporte_deudas():
    """Reporte de deudas por cliente"""
    db = get_db()
    try:
        deudas = db.execute('''
            SELECT 
                c.rut,
                c.razon_social,
                COUNT(d.id) as cantidad_facturas,
                COALESCE(SUM(d.valor_total), 0) as total_deuda
            FROM clientes c
            LEFT JOIN facturas d ON c.rut = d.cliente_rut AND d.estado = 'Pendiente'
            WHERE c.activo = 1
            GROUP BY c.rut, c.razon_social
            HAVING total_deuda > 0
            ORDER BY total_deuda DESC
        ''').fetchall()
        return jsonify([dict(row) for row in deudas])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reporte-nc-nd')
@login_required
def api_reporte_nc_nd():
    """Reporte de notas de crédito y débito"""
    db = get_db()
    try:
        notas = db.execute('''
            SELECT 
                d.*,
                c.razon_social,
                dr.numero_doc as doc_referencia_numero,
                dr.tipo_doc as doc_referencia_tipo
            FROM facturas d
            LEFT JOIN clientes c ON d.cliente_rut = c.rut
            LEFT JOIN facturas dr ON d.factura_referencia_id = dr.id
            WHERE d.tipo_doc IN ('NC', 'ND')
            ORDER BY d.fecha_emision DESC
        ''').fetchall()
        return jsonify([dict(row) for row in notas])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reporte-resumen')
@login_required
def api_reporte_resumen():
    """Resumen general para el dashboard"""
    db = get_db()
    try:
        total_facturado_result = db.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM facturas WHERE tipo_doc IN ('FAC', 'BOL') AND estado != 'Anulado'").fetchone()
        total_facturado = total_facturado_result['total'] if total_facturado_result else 0.0
        
        total_pagado_result = db.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM facturas WHERE estado = 'Pagado'").fetchone()
        total_pagado = total_pagado_result['total'] if total_pagado_result else 0.0

        total_pendiente_result = db.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM facturas WHERE estado = 'Pendiente'").fetchone()
        total_pendiente = total_pendiente_result['total'] if total_pendiente_result else 0.0

        total_nc_result = db.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM facturas WHERE tipo_doc = 'NC'").fetchone()
        total_nc = total_nc_result['total'] if total_nc_result else 0.0

        total_nd_result = db.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM facturas WHERE tipo_doc = 'ND'").fetchone()
        total_nd = total_nd_result['total'] if total_nd_result else 0.0
        
        count_pagados = db.execute("SELECT COUNT(*) FROM facturas WHERE estado = 'Pagado'").fetchone()[0] or 0
        count_pendientes = db.execute("SELECT COUNT(*) FROM facturas WHERE estado = 'Pendiente'").fetchone()[0] or 0
        count_nc = db.execute("SELECT COUNT(*) FROM facturas WHERE tipo_doc = 'NC'").fetchone()[0] or 0
        count_anulados = db.execute("SELECT COUNT(*) FROM facturas WHERE estado = 'Anulado'").fetchone()[0] or 0
        
        resumen = {
            'total_facturado': float(total_facturado),
            'total_pagado': float(total_pagado),
            'total_pendiente': float(total_pendiente),
            'total_nc': float(total_nc),
            'total_nd': float(total_nd),
            'count_pagados': count_pagados,
            'count_pendientes': count_pendientes,
            'count_nc': count_nc,
            'count_anulados': count_anulados
        }
        return jsonify(resumen)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reporte-ventas-mensual')
@login_required
def api_reporte_ventas_mensual():
    """Reporte de ventas mensuales"""
    db = get_db()
    try:
        ventas_mensual = db.execute('''
            SELECT 
                strftime('%Y-%m', fecha_emision) as mes,
                tipo_doc,
                COUNT(*) as cantidad,
                SUM(valor_total) as total_ventas
            FROM facturas 
            WHERE tipo_doc IN ('FAC', 'BOL') AND estado != 'Anulado'
            GROUP BY mes, tipo_doc
            ORDER BY mes DESC
        ''').fetchall()
        return jsonify([dict(row) for row in ventas_mensual])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reporte-top-clientes')
@login_required
def api_reporte_top_clientes():
    """Top 10 clientes por facturación"""
    db = get_db()
    try:
        top_clientes = db.execute('''
            SELECT 
                c.razon_social,
                c.rut,
                COUNT(d.id) as total_facturas,
                SUM(d.valor_total) as total_facturado
            FROM clientes c
            LEFT JOIN facturas d ON c.rut = d.cliente_rut 
            WHERE d.estado != 'Anulado' AND d.tipo_doc IN ('FAC', 'BOL')
            GROUP BY c.rut, c.razon_social
            ORDER BY total_facturado DESC
            LIMIT 10
        ''').fetchall()
        return jsonify([dict(row) for row in top_clientes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reporte-anual')
@login_required
def api_reporte_anual():
    """Reporte anual"""
    anio = request.args.get('anio', str(datetime.now().year))
    db = get_db()
    
    try:
        # Totales anuales
        total_facturado_anual = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND tipo_doc IN ('FAC', 'BOL') AND estado != 'Anulado'", (anio,)).fetchone()[0] or 0
        total_pagado_anual = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND estado = 'Pagado'", (anio,)).fetchone()[0] or 0
        total_pendiente_anual = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND estado = 'Pendiente'", (anio,)).fetchone()[0] or 0
        total_facturas = db.execute(f"SELECT COUNT(*) FROM facturas WHERE strftime('%Y', fecha_emision) = ?", (anio,)).fetchone()[0] or 0
        total_facturas = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND tipo_doc = 'FAC' AND estado != 'Anulado'", (anio,)).fetchone()[0] or 0
        total_boletas = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND tipo_doc = 'BOL' AND estado != 'Anulado'", (anio,)).fetchone()[0] or 0
        total_notas_credito = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND tipo_doc = 'NC'", (anio,)).fetchone()[0] or 0
        total_notas_debito = db.execute(f"SELECT COALESCE(SUM(valor_total), 0) FROM facturas WHERE strftime('%Y', fecha_emision) = ? AND tipo_doc = 'ND'", (anio,)).fetchone()[0] or 0
        
        # Ventas mensuales
        ventas_mensuales_rows = db.execute(f'''
            SELECT 
                strftime('%Y-%m', fecha_emision) as mes,
                SUM(CASE WHEN tipo_doc = 'FAC' THEN valor_total ELSE 0 END) as total_facturas,
                SUM(CASE WHEN tipo_doc = 'BOL' THEN valor_total ELSE 0 END) as total_boletas,
                SUM(CASE WHEN tipo_doc IN ('FAC', 'BOL') THEN valor_total ELSE 0 END) as total_ventas
            FROM facturas
            WHERE strftime('%Y', fecha_emision) = ? AND estado != 'Anulado'
            GROUP BY mes
            ORDER BY mes
        ''', (anio,)).fetchall()
        
        reporte = {
            'total_facturado_anual': total_facturado_anual,
            'total_pagado_anual': total_pagado_anual,
            'total_pendiente_anual': total_pendiente_anual,
            'total_facturas': total_facturas,
            'total_facturas': total_facturas,
            'total_boletas': total_boletas,
            'total_notas_credito': total_notas_credito,
            'total_notas_debito': total_notas_debito,
            'ventas_mensuales': [dict(row) for row in ventas_mensuales_rows]
        }
        
        return jsonify(reporte)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/exportar-reporte-anual-excel')
@login_required
def api_exportar_reporte_anual_excel():
    """Exportar reporte anual a Excel con formato mejorado"""
    anio = request.args.get('anio', str(datetime.now().year))
    db = get_db()
    
    try:
        # Obtener los datos del reporte anual
        ventas_mensuales_df = pd.read_sql(f'''
            SELECT 
                strftime('%Y-%m', fecha_emision) as "Mes",
                SUM(CASE WHEN tipo_doc = 'FAC' THEN valor_total ELSE 0 END) as "Facturas",
                SUM(CASE WHEN tipo_doc = 'BOL' THEN valor_total ELSE 0 END) as "Boletas",
                SUM(CASE WHEN tipo_doc IN ('FAC', 'BOL') THEN valor_total ELSE 0 END) as "Total Ventas"
            FROM facturas
            WHERE strftime('%Y', fecha_emision) = ? AND estado != 'Anulado'
            GROUP BY "Mes"
            ORDER BY "Mes"
        ''', db, params=(anio,))

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            ventas_mensuales_df.to_excel(writer, sheet_name=f'Reporte Anual {anio}', index=False, startrow=3)
            
            workbook = writer.book
            worksheet = writer.sheets[f'Reporte Anual {anio}']

            # Formatos
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 18,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4F81BD',
                'font_color': 'white',
                'border': 1
            })
            
            subtitle_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'font_color': '#666666'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#DCE6F1',
                'border': 1,
                'align': 'center',
                'font_color': '#4F81BD'
            })

            money_format = workbook.add_format({'num_format': '$#,##0', 'align': 'right', 'border': 1})
            
            # Títulos
            worksheet.merge_range('A1:D1', f'REPORTE ANUAL {anio} - TEKNETAU', title_format)
            worksheet.merge_range('A2:D2', f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', subtitle_format)

            # Headers
            for col_num, value in enumerate(ventas_mensuales_df.columns.values):
                worksheet.write(3, col_num, value, header_format)

            # Formato columnas
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:D', 15, money_format)

            # Congelar paneles
            worksheet.freeze_panes(4, 0)

        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename=reporte_anual_{anio}.xlsx"}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/exportar-ventas-excel')
@login_required
def api_exportar_ventas_excel():
    """Exportar reporte de ventas mensuales a Excel con formato mejorado"""
    db = get_db()
    try:
        ventas_mensual_df = pd.read_sql('''
            SELECT 
                strftime('%Y-%m', fecha_emision) as "Mes",
                tipo_doc as "Tipo Documento",
                COUNT(*) as "Cantidad",
                SUM(valor_neto) as "Subtotal",
                SUM(iva) as "IVA",
                SUM(valor_total) as "Total"
            FROM facturas 
            WHERE tipo_doc IN ('FAC', 'BOL') AND estado != 'Anulado'
            GROUP BY "Mes", "Tipo Documento"
            ORDER BY "Mes" DESC
        ''', db)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            ventas_mensual_df.to_excel(writer, sheet_name='Ventas Mensuales', index=False, startrow=3)
            
            workbook = writer.book
            worksheet = writer.sheets['Ventas Mensuales']

            # Formatos
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 18,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4F81BD',
                'font_color': 'white',
                'border': 1
            })
            
            subtitle_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'font_color': '#666666'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#DCE6F1',
                'border': 1,
                'align': 'center',
                'font_color': '#4F81BD'
            })

            money_format = workbook.add_format({'num_format': '$#,##0', 'align': 'right', 'border': 1})
            
            # Títulos
            worksheet.merge_range('A1:F1', 'REPORTE DE VENTAS MENSUALES - TEKNETAU', title_format)
            worksheet.merge_range('A2:F2', f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', subtitle_format)

            # Headers
            for col_num, value in enumerate(ventas_mensual_df.columns.values):
                worksheet.write(3, col_num, value, header_format)

            # Formato columnas
            worksheet.set_column('A:B', 15)
            worksheet.set_column('C:C', 10)
            worksheet.set_column('D:F', 15, money_format)

            # Congelar paneles
            worksheet.freeze_panes(4, 0)
            
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment;filename=reporte_ventas_mensuales.xlsx"}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/exportar-top-clientes-excel')
@login_required
def api_exportar_top_clientes_excel():
    """Exportar top 10 clientes a Excel con formato mejorado"""
    db = get_db()
    try:
        top_clientes_df = pd.read_sql('''
            SELECT 
                c.razon_social as "Cliente",
                c.rut as "RUT",
                COUNT(d.id) as "Total Documentos",
                SUM(d.valor_total) as "Total Facturado"
            FROM clientes c
            LEFT JOIN facturas d ON c.rut = d.cliente_rut 
            WHERE d.estado != 'Anulado' AND d.tipo_doc IN ('FAC', 'BOL')
            GROUP BY c.rut, c.razon_social
            ORDER BY "Total Facturado" DESC
            LIMIT 10
        ''', db)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            top_clientes_df.to_excel(writer, sheet_name='Top 10 Clientes', index=False, startrow=3)

            workbook = writer.book
            worksheet = writer.sheets['Top 10 Clientes']

            # Formatos
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 18,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4F81BD',
                'font_color': 'white',
                'border': 1
            })
            
            subtitle_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'font_color': '#666666'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#DCE6F1',
                'border': 1,
                'align': 'center',
                'font_color': '#4F81BD'
            })

            money_format = workbook.add_format({'num_format': '$#,##0', 'align': 'right', 'border': 1})
            
            # Títulos
            worksheet.merge_range('A1:D1', 'REPORTE DE TOP 10 CLIENTES - TEKNETAU', title_format)
            worksheet.merge_range('A2:D2', f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', subtitle_format)

            # Headers
            for col_num, value in enumerate(top_clientes_df.columns.values):
                worksheet.write(3, col_num, value, header_format)

            # Formato columnas
            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 18)
            worksheet.set_column('D:D', 18, money_format)

            # Congelar paneles
            worksheet.freeze_panes(4, 0)
            
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment;filename=reporte_top_10_clientes.xlsx"}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/facturas/<int:factura_id>/estado', methods=['PUT'])
@login_required
def api_actualizar_estado_factura(factura_id):
    """API para actualizar el estado de una factura."""
    data = request.get_json()
    nuevo_estado = data.get('estado')

    if not nuevo_estado or nuevo_estado not in ['Pendiente', 'Pagado', 'Anulado']:
        return jsonify({'success': False, 'error': 'Estado no válido'}), 400

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE facturas SET estado = ? WHERE id = ?", (nuevo_estado, factura_id))
        db.commit()
        return jsonify({'success': True, 'message': 'Estado de la factura actualizado correctamente.'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/proyectos-por-cliente/<string:cliente_rut>')
@login_required
def api_proyectos_por_cliente(cliente_rut):
    """API para obtener los proyectos de un cliente específico."""
    app.logger.info(f"API call: api_proyectos_por_cliente for RUT: {cliente_rut}")
    db = get_db()
    try:
        proyectos = db.execute(
            "SELECT codigo, nombre FROM proyectos WHERE cliente_rut = ? AND estado = 'Activo'",
            (cliente_rut,)
        ).fetchall()
        proyectos_list = [dict(p) for p in proyectos]
        app.logger.info(f"Found {len(proyectos_list)} projects for RUT {cliente_rut}: {proyectos_list}")
        return jsonify(proyectos_list)
    except Exception as e:
        app.logger.error(f"Error in api_proyectos_por_cliente for RUT {cliente_rut}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/facturas-referencia/<cliente_rut>')
@login_required
def api_facturas_referencia(cliente_rut):
    """Obtener facturas de referencia para NC/ND por cliente"""
    db = get_db()
    facturas = db.execute('''
        SELECT d.id, d.numero_doc, d.tipo_doc, d.valor_total, d.fecha_emision, d.estado
        FROM facturas d 
        WHERE d.cliente_rut = ? AND d.tipo_doc IN ('FAC', 'BOL') AND d.estado != 'Anulado'
        ORDER BY d.fecha_emision DESC
    ''', (cliente_rut,)).fetchall()
    return jsonify([dict(row) for row in facturas])



@app.route('/api/generar-boleta-rapida', methods=['POST'])
@login_required
def api_generar_boleta_rapida():
    """Generar boleta rápida desde el dashboard"""
    data = request.get_json()
    db = get_db()
    
    try:
        # Obtener próximo número de boleta
        ultima_boleta = get_ultimo_numero_factura('BOL')
        numero_boleta = ultima_boleta + 1
        
        # Insertar documento
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO facturas 
            (numero_doc, tipo_doc, fecha_emision, cliente_rut, descripcion, 
             valor_neto, iva, valor_total, estado, forma_pago, usuario_creacion)
            VALUES (?, 'BOL', date('now'), ?, ?, ?, ?, ?, 'Pendiente', 'Contado', ?)
        ''', (
            numero_boleta,
            data['cliente_rut'],
            data['descripcion'],
            data['valor_neto'],
            data['iva'],
            data['valor_total'],
            session['username']
        ))
        
        factura_id = cursor.lastrowid
        
        # Insertar item único
        cursor.execute('''
            INSERT INTO factura_items 
            (factura_id, descripcion, cantidad, precio_unitario, total_linea)
            VALUES (?, ?, 1, ?, ?)
        ''', (
            factura_id,
            data['descripcion'],
            data['valor_neto'],
            data['valor_neto']
        ))
        
        db.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Boleta generada exitosamente',
            'numero_boleta': numero_boleta
        })
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ===== FUNCIONES DE EXPORTACIÓN MEJORADAS =====

@app.route('/api/exportar-reporte-deudas-excel')
@login_required
def api_exportar_reporte_deudas_excel():
    """Exportar reporte de deudas a Excel con formato mejorado y detallado."""
    db = get_db()
    
    try:
        # 1. Datos para la hoja de Resumen por Cliente
        deudas_summary_df = pd.read_sql('''
            SELECT 
                c.razon_social as "Cliente",
                c.rut as "RUT",
                COUNT(d.id) as "Documentos Pendientes",
                COALESCE(SUM(d.valor_total), 0) as "Total Deuda"
            FROM clientes c
            JOIN facturas d ON c.rut = d.cliente_rut AND d.estado = 'Pendiente'
            WHERE c.activo = 1
            GROUP BY c.rut, c.razon_social
            HAVING "Total Deuda" > 0
            ORDER BY "Total Deuda" DESC
        ''', db)

        # 2. Datos para la hoja de Detalle de Documentos
        deudas_detail_df = pd.read_sql('''
            SELECT
                c.razon_social as "Cliente",
                d.numero_doc as "N° Documento",
                d.tipo_doc as "Tipo",
                d.fecha_emision as "Fecha Emisión",
                d.fecha_vencimiento as "Fecha Vencimiento",
                d.valor_total as "Monto",
                JULIANDAY('now') - JULIANDAY(d.fecha_vencimiento) as "Días Vencido"
            FROM facturas d
            JOIN clientes c ON d.cliente_rut = c.rut
            WHERE d.estado = 'Pendiente'
            ORDER BY "Días Vencido" DESC
        ''', db)
        # Convertir fechas a formato legible
        deudas_detail_df["Fecha Emisión"] = pd.to_datetime(deudas_detail_df["Fecha Emisión"]).dt.strftime('%d-%m-%Y')
        deudas_detail_df["Fecha Vencimiento"] = pd.to_datetime(deudas_detail_df["Fecha Vencimiento"]).dt.strftime('%d-%m-%Y')


        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # --- Hoja 1: Resumen de Deudas ---
            deudas_summary_df.to_excel(writer, sheet_name='Resumen Deudas', index=False, startrow=4)
            
            # --- Hoja 2: Detalle de Documentos ---
            deudas_detail_df.to_excel(writer, sheet_name='Detalle Documentos', index=False, startrow=4)

            # --- Formatos Comunes ---
            workbook = writer.book
            money_format = workbook.add_format({'num_format': '$#,##0', 'align': 'right', 'border': 1})
            date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'align': 'center', 'border': 1})
            header_format_summary = workbook.add_format({'bold': True, 'fg_color': '#D32F2F', 'font_color': 'white', 'border': 1, 'align': 'center'})
            header_format_detail = workbook.add_format({'bold': True, 'fg_color': '#4F81BD', 'font_color': 'white', 'border': 1, 'align': 'center'})
            title_format = workbook.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter'})

            # --- Diseño Hoja 1: Resumen ---
            ws_summary = writer.sheets['Resumen Deudas']
            ws_summary.merge_range('A1:D2', 'Reporte de Deudas Pendientes por Cliente', title_format)
            ws_summary.merge_range('A3:D3', f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', workbook.add_format({'align': 'center'}))
            
            for col_num, value in enumerate(deudas_summary_df.columns.values):
                ws_summary.write(4, col_num, value, header_format_summary)

            ws_summary.set_column('A:A', 35) # Cliente
            ws_summary.set_column('B:B', 15) # RUT
            ws_summary.set_column('C:C', 20) # Documentos Pendientes
            ws_summary.set_column('D:D', 18, money_format) # Total Deuda
            
            # --- Diseño Hoja 2: Detalle ---
            ws_detail = writer.sheets['Detalle Documentos']
            ws_detail.merge_range('A1:G2', 'Detalle de Todos los Documentos Pendientes', title_format)
            ws_detail.merge_range('A3:G3', f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', workbook.add_format({'align': 'center'}))

            for col_num, value in enumerate(deudas_detail_df.columns.values):
                ws_detail.write(4, col_num, value, header_format_detail)

            ws_detail.set_column('A:A', 35) # Cliente
            ws_detail.set_column('B:C', 15) # N° Doc, Tipo
            ws_detail.set_column('D:E', 18, date_format) # Fechas
            ws_detail.set_column('F:F', 18, money_format) # Monto
            ws_detail.set_column('G:G', 15) # Días Vencido

            # Formato condicional para días vencidos
            ws_detail.conditional_format('G5:G100', {'type': '3_color_scale', 'min_color': "#63BE7B", 'mid_color': "#FFEB84", 'max_color': "#F8696B"})

        output.seek(0)
        
        fecha_export = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"reporte_detallado_deudas_{fecha_export}.xlsx"
        
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/reportes-proyectos')
@login_required
def reportes_proyectos():
    """Página de reporte de proyectos"""
    return render_template('reportes_proyectos.html')

@app.route('/api/reporte-proyectos')
@login_required
def api_reporte_proyectos():
    """Reporte de estado de proyectos"""
    db = get_db()
    try:
        proyectos = db.execute('''
            SELECT 
                p.codigo,
                p.nombre,
                p.presupuesto,
                p.estado,
                c.razon_social,
                (SELECT COALESCE(SUM(f.valor_total), 0) 
                 FROM facturas f 
                 WHERE f.proyecto_codigo = p.codigo AND f.tipo_doc IN ('FAC', 'BOL') AND f.estado != 'Anulado') as total_facturado
            FROM proyectos p
            LEFT JOIN clientes c ON p.cliente_rut = c.rut
            WHERE p.estado != 'Inactivo'
            ORDER BY p.estado, p.nombre
        ''').fetchall()
        return jsonify([dict(row) for row in proyectos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reporte-proyectos/exportar-excel')
@login_required
def exportar_reporte_proyectos_excel():
    """Exportar reporte de proyectos a Excel"""
    db = get_db()
    try:
        query = '''
            SELECT 
                p.nombre as "Proyecto",
                p.codigo as "Código",
                c.razon_social as "Cliente",
                p.presupuesto as "Presupuesto",
                (SELECT COALESCE(SUM(f.valor_total), 0) 
                 FROM facturas f 
                 WHERE f.proyecto_codigo = p.codigo AND f.tipo_doc IN ('FAC', 'BOL') AND f.estado != 'Anulado') as "Total Facturado",
                (p.presupuesto - (SELECT COALESCE(SUM(f.valor_total), 0) 
                                  FROM facturas f 
                                  WHERE f.proyecto_codigo = p.codigo AND f.tipo_doc IN ('FAC', 'BOL') AND f.estado != 'Anulado')) as "Saldo Pendiente",
                p.estado as "Estado"
            FROM proyectos p
            LEFT JOIN clientes c ON p.cliente_rut = c.rut
            WHERE p.estado != 'Inactivo'
            ORDER BY p.estado, "Proyecto"
        '''
        df = pd.read_sql_query(query, db)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Reporte de Proyectos', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Reporte de Proyectos']
            
            money_format = workbook.add_format({'num_format': '$#,##0'})
            worksheet.set_column('D:F', 15, money_format)
            worksheet.set_column('A:A', 30)
            worksheet.set_column('C:C', 30)

        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment;filename=reporte_proyectos.xlsx"}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/facturas', methods=['GET'])
@login_required
def api_facturas():
    """API para obtener facturas, con filtro opcional por proyecto."""
    db = get_db()
    proyecto_codigo = request.args.get('proyecto_codigo')

    if proyecto_codigo:
        # Filtrar por proyecto
        query = '''
            SELECT f.*, c.razon_social FROM facturas f
            LEFT JOIN clientes c ON f.cliente_rut = c.rut
            WHERE f.proyecto_codigo = ?
            ORDER BY f.fecha_emision DESC
        '''
        facturas = db.execute(query, (proyecto_codigo,)).fetchall()
    else:
        # Sin filtro (comportamiento original si es necesario)
        query = '''
            SELECT f.*, c.razon_social FROM facturas f
            LEFT JOIN clientes c ON f.cliente_rut = c.rut
            ORDER BY f.fecha_emision DESC
        '''
        facturas = db.execute(query).fetchall()

    return jsonify([dict(row) for row in facturas])


def get_ultimo_numero_factura(tipo_doc):
    """Obtener el último número de documento por tipo"""
    db = get_db()
    resultado = db.execute(
        "SELECT COALESCE(MAX(numero_doc), 0) FROM facturas WHERE tipo_doc = ?", 
        (tipo_doc,)
    ).fetchone()[0]
    return resultado
