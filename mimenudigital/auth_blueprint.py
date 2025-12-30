"""
auth_blueprint.py

Módulo que registra las rutas de autenticación directamente en la app.
Usamos una función `register_auth(app)` para evitar problemas de importación circular
al tiempo que mantenemos los nombres de endpoints actuales.
"""

from flask import request, render_template, flash, redirect, url_for, session
from werkzeug.security import check_password_hash
import traceback


def register_auth(app, get_db, dict_from_row):
    """Registra rutas de auth en la app existente.

    Args:
        app: instancia Flask
        get_db: función para obtener conexión DB (pasada desde app_menu)
        dict_from_row: helper para convertir filas a dict
    """

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Página de inicio de sesión."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            try:
                db = get_db()
                with db.cursor() as cur:
                    cur.execute('''
                        SELECT u.*, r.nombre as restaurante_nombre 
                        FROM usuarios_admin u
                        LEFT JOIN restaurantes r ON u.restaurante_id = r.id
                        WHERE u.username = %s AND u.activo = 1
                    ''', (username,))
                    row = cur.fetchone()

                    if row and check_password_hash(row.get('password_hash', ''), password):
                        user = dict_from_row(row)
                        session['user_id'] = user['id']
                        session['username'] = user['username']
                        session['nombre'] = user.get('nombre')
                        session['rol'] = user.get('rol')
                        session['restaurante_id'] = user.get('restaurante_id')
                        session['restaurante_nombre'] = user.get('restaurante_nombre') or 'Panel Admin'

                        cur.execute("UPDATE usuarios_admin SET ultimo_login = NOW() WHERE id = %s", (user['id'],))
                        db.commit()

                        flash('Bienvenido ' + (user.get('nombre') or ''), 'success')
                        if user.get('rol') == 'superadmin':
                            return redirect(url_for('superadmin_restaurantes'))
                        return redirect(url_for('menu_gestion'))

                flash('Usuario o contraseña incorrectos', 'error')
            except Exception as e:
                app.logger.error(f"Error en login: {e}")
                app.logger.debug(traceback.format_exc())
                flash('Error al procesar la solicitud', 'error')

        return render_template('login.html')


    @app.route('/logout')
    def logout():
        session.clear()
        flash('Sesión cerrada correctamente', 'info')
        return redirect(url_for('login'))


    @app.route('/recuperar-contraseña', methods=['GET', 'POST'])
    def recuperar_contraseña():
        """Solicita recuperación de contraseña."""
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            if not email:
                flash('Por favor ingresa tu email', 'error')
                return render_template('recuperar_contraseña.html')

            try:
                app.logger.info(f"Password reset requested for {email}")
                flash('Si el email está registrado, recibirás instrucciones en breve', 'info')
            except Exception as e:
                app.logger.error(f"Error en recuperar_contraseña: {e}")
                app.logger.debug(traceback.format_exc())
                flash('Error al procesar la solicitud', 'error')

        return render_template('recuperar_contraseña.html')


    @app.route('/resetear-contraseña/<token>', methods=['GET', 'POST'])
    def resetear_contraseña(token):
        """Permite resetear la contraseña con un token válido (placeholder)."""
        return render_template('resetear_contraseña.html', token=token)

    # Return the app for chaining if desired
    return app
