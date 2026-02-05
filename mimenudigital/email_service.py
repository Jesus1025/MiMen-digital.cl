# ============================================================
# SERVICIO DE EMAIL - MENÚ DIGITAL SAAS
# Divergent Studio - 2026
# ============================================================

import logging
import os
from functools import wraps
from threading import Thread

logger = logging.getLogger(__name__)

# Intentar importar Flask-Mail
try:
    from flask_mail import Mail, Message
    FLASK_MAIL_AVAILABLE = True
except ImportError:
    FLASK_MAIL_AVAILABLE = False
    logger.warning("Flask-Mail no está instalado. pip install Flask-Mail")

# Instancia global de Mail
mail = None


def init_mail(app):
    """Inicializa Flask-Mail con la aplicación."""
    global mail
    
    if not FLASK_MAIL_AVAILABLE:
        logger.warning("Flask-Mail no disponible, emails deshabilitados")
        return None
    
    # Verificar configuración mínima
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        logger.warning("MAIL_USERNAME o MAIL_PASSWORD no configurados. Emails deshabilitados.")
        return None
    
    mail = Mail(app)
    logger.info("✅ Flask-Mail inicializado correctamente")
    return mail


def is_mail_configured():
    """Verifica si el servicio de email está configurado."""
    return mail is not None and FLASK_MAIL_AVAILABLE


def send_async_email(app, msg):
    """Envía email de forma asíncrona."""
    with app.app_context():
        try:
            mail.send(msg)
            logger.info("Email enviado a: %s", msg.recipients)
        except Exception as e:
            logger.error("Error enviando email: %s", str(e))


def send_email(subject, recipients, html_body, text_body=None, sender=None, async_send=True):
    """
    Envía un email.
    
    Args:
        subject: Asunto del email
        recipients: Lista de destinatarios o string único
        html_body: Cuerpo HTML del email
        text_body: Cuerpo de texto plano (opcional)
        sender: Remitente (opcional, usa default)
        async_send: Si True, envía en un thread separado
    
    Returns:
        bool: True si se envió correctamente
    """
    if not is_mail_configured():
        logger.warning("Email no enviado (servicio no configurado): %s", subject)
        return False
    
    # Importar app aquí para evitar circular imports
    from flask import current_app
    
    if isinstance(recipients, str):
        recipients = [recipients]
    
    msg = Message(
        subject=subject,
        recipients=recipients,
        html=html_body,
        body=text_body or html_body,
        sender=sender or current_app.config.get('MAIL_DEFAULT_SENDER')
    )
    
    if async_send:
        # Enviar en thread separado para no bloquear
        Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        ).start()
        return True
    else:
        try:
            mail.send(msg)
            logger.info("Email enviado sincrónicamente a: %s", recipients)
            return True
        except Exception as e:
            logger.error("Error enviando email: %s", str(e))
            return False


# ============================================================
# TEMPLATES DE EMAIL
# ============================================================

def get_email_template(template_name, **kwargs):
    """Genera el HTML de un email basado en template."""
    
    # Estilos base
    base_style = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .email-container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .email-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .email-header h1 { margin: 0; font-size: 24px; }
        .email-body { background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; }
        .email-footer { background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; border-top: none; }
        .btn { display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .btn:hover { opacity: 0.9; }
        .info-box { background: #f0f8ff; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }
        .warning-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; }
        .success-box { background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; }
        .ticket-info { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .ticket-info strong { color: #2c3e50; }
        .priority-urgente { color: #e74c3c; font-weight: bold; }
        .priority-alta { color: #f39c12; font-weight: bold; }
        .priority-media { color: #3498db; }
        .priority-baja { color: #95a5a6; }
    </style>
    """
    
    templates = {
        # ============================================================
        # EMAIL: Nuevo ticket recibido (para el usuario)
        # ============================================================
        'ticket_recibido': f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>🎫 Ticket Recibido</h1>
                </div>
                <div class="email-body">
                    <p>Hola <strong>{{{{ nombre }}}}</strong>,</p>
                    
                    <p>Hemos recibido tu mensaje de soporte. Nuestro equipo lo revisará y te responderá lo antes posible.</p>
                    
                    <div class="ticket-info">
                        <p><strong>Número de ticket:</strong> #{{{{ ticket_id }}}}</p>
                        <p><strong>Asunto:</strong> {{{{ asunto }}}}</p>
                        <p><strong>Tipo:</strong> {{{{ tipo }}}}</p>
                        <p><strong>Fecha:</strong> {{{{ fecha }}}}</p>
                    </div>
                    
                    <div class="info-box">
                        <p>📋 <strong>Tu mensaje:</strong></p>
                        <p style="white-space: pre-wrap;">{{{{ mensaje }}}}</p>
                    </div>
                    
                    <p>Tiempo estimado de respuesta: <strong>24-48 horas hábiles</strong></p>
                    
                    <p>Si tienes información adicional, puedes responder a este email.</p>
                </div>
                <div class="email-footer">
                    <p>© {{{{ year }}}} Menú Digital - Divergent Studio</p>
                    <p>Este es un mensaje automático, por favor no respondas directamente.</p>
                </div>
            </div>
        </body>
        </html>
        """,
        
        # ============================================================
        # EMAIL: Notificación de nuevo ticket (para superadmin)
        # ============================================================
        'ticket_nuevo_admin': f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="email-container">
                <div class="email-header" style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
                    <h1>🚨 Nuevo Ticket de Soporte</h1>
                </div>
                <div class="email-body">
                    <p>Se ha recibido un nuevo ticket de soporte:</p>
                    
                    <div class="ticket-info">
                        <p><strong>Ticket #{{{{ ticket_id }}}}</strong></p>
                        <p><strong>De:</strong> {{{{ nombre }}}} ({{{{ email }}}})</p>
                        {{{{ telefono_html }}}}
                        <p><strong>Tipo:</strong> {{{{ tipo }}}}</p>
                        <p><strong>Prioridad:</strong> <span class="priority-{{{{ prioridad }}}}">{{{{ prioridad_display }}}}</span></p>
                        {{{{ restaurante_html }}}}
                    </div>
                    
                    <p><strong>Asunto:</strong> {{{{ asunto }}}}</p>
                    
                    <div class="info-box">
                        <p><strong>Mensaje:</strong></p>
                        <p style="white-space: pre-wrap;">{{{{ mensaje }}}}</p>
                    </div>
                    
                    <p style="text-align: center; margin-top: 25px;">
                        <a href="{{{{ admin_url }}}}" class="btn">Ver en Panel de Admin</a>
                    </p>
                </div>
                <div class="email-footer">
                    <p>Panel de SuperAdmin - Menú Digital</p>
                </div>
            </div>
        </body>
        </html>
        """,
        
        # ============================================================
        # EMAIL: Respuesta a ticket (para el usuario)
        # ============================================================
        'ticket_respuesta': f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="email-container">
                <div class="email-header" style="background: linear-gradient(135deg, #27ae60 0%, #1e8449 100%);">
                    <h1>✅ Respuesta a tu Ticket</h1>
                </div>
                <div class="email-body">
                    <p>Hola <strong>{{{{ nombre }}}}</strong>,</p>
                    
                    <p>Hemos respondido a tu ticket de soporte:</p>
                    
                    <div class="ticket-info">
                        <p><strong>Ticket #{{{{ ticket_id }}}}</strong></p>
                        <p><strong>Asunto:</strong> {{{{ asunto }}}}</p>
                    </div>
                    
                    <div class="success-box">
                        <p><strong>💬 Nuestra respuesta:</strong></p>
                        <p style="white-space: pre-wrap;">{{{{ respuesta }}}}</p>
                    </div>
                    
                    {{{{ mensaje_original_html }}}}
                    
                    <p>Si necesitas más ayuda, puedes responder a este email o crear un nuevo ticket.</p>
                    
                    <p>¡Gracias por usar nuestros servicios!</p>
                </div>
                <div class="email-footer">
                    <p>© {{{{ year }}}} Menú Digital - Divergent Studio</p>
                </div>
            </div>
        </body>
        </html>
        """,
        
        # ============================================================
        # EMAIL: Recuperación de contraseña
        # ============================================================
        'password_reset': f"""
        <!DOCTYPE html>
        <html>
        <head>{base_style}</head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>🔐 Recuperar Contraseña</h1>
                </div>
                <div class="email-body">
                    <p>Hola <strong>{{{{ nombre }}}}</strong>,</p>
                    
                    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en Menú Digital.</p>
                    
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{{{{ reset_url }}}}" class="btn">Restablecer Contraseña</a>
                    </p>
                    
                    <div class="warning-box">
                        <p>⚠️ Este enlace expirará en <strong>24 horas</strong>.</p>
                        <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
                    </div>
                    
                    <p style="font-size: 12px; color: #666;">
                        Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                        <code style="word-break: break-all;">{{{{ reset_url }}}}</code>
                    </p>
                </div>
                <div class="email-footer">
                    <p>© {{{{ year }}}} Menú Digital - Divergent Studio</p>
                    <p>Por seguridad, nunca compartas este enlace con nadie.</p>
                </div>
            </div>
        </body>
        </html>
        """
    }
    
    template = templates.get(template_name, '')
    
    # Reemplazar variables
    from datetime import datetime
    kwargs['year'] = datetime.now().year
    
    for key, value in kwargs.items():
        template = template.replace('{{{{ ' + key + ' }}}}', str(value) if value else '')
        template = template.replace('{{{{' + key + '}}}}', str(value) if value else '')
    
    return template


# ============================================================
# FUNCIONES DE ENVÍO ESPECÍFICAS
# ============================================================

def enviar_confirmacion_ticket(ticket_data):
    """
    Envía email de confirmación al usuario cuando crea un ticket.
    Usa la configuración del panel de admin si está disponible.
    
    Args:
        ticket_data: dict con id, nombre, email, asunto, mensaje, tipo, fecha
    """
    from datetime import datetime
    
    # Obtener configuración personalizada
    nombre_empresa = 'Menú Digital'
    mensaje_auto = None
    try:
        from app_menu import get_config_global
        config = get_config_global()
        nombre_empresa = config.get('soporte_nombre_empresa') or 'Menú Digital'
        mensaje_auto = config.get('soporte_mensaje_auto')
    except Exception:
        pass
    
    html = get_email_template('ticket_recibido',
        nombre=ticket_data.get('nombre', 'Usuario'),
        ticket_id=ticket_data.get('id'),
        asunto=ticket_data.get('asunto'),
        tipo=ticket_data.get('tipo', 'Consulta').replace('_', ' ').title(),
        mensaje=ticket_data.get('mensaje'),
        fecha=ticket_data.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M')),
        nombre_empresa=nombre_empresa,
        mensaje_auto=mensaje_auto
    )
    
    return send_email(
        subject=f"[{nombre_empresa}] Ticket #{ticket_data.get('id')} - Hemos recibido tu mensaje",
        recipients=ticket_data.get('email'),
        html_body=html
    )


def notificar_nuevo_ticket_admin(ticket_data, admin_url):
    """
    Notifica al superadmin sobre un nuevo ticket.
    Usa el email de soporte configurado en el panel de admin.
    
    Args:
        ticket_data: dict con datos del ticket
        admin_url: URL al panel de admin
    """
    from flask import current_app
    
    # Primero intentar obtener el email de la configuración global
    admin_email = None
    try:
        # Importar aquí para evitar circular import
        from app_menu import get_config_global
        config = get_config_global()
        admin_email = config.get('soporte_email')
    except Exception as e:
        logger.warning("No se pudo obtener soporte_email de config: %s", e)
    
    # Fallback al email del config de Flask
    if not admin_email:
        admin_email = current_app.config.get('SUPERADMIN_EMAIL')
    
    if not admin_email:
        logger.warning("No hay email de soporte configurado (ni soporte_email ni SUPERADMIN_EMAIL)")
        return False
    
    telefono_html = ''
    if ticket_data.get('telefono'):
        telefono_html = f"<p><strong>Teléfono:</strong> {ticket_data.get('telefono')}</p>"
    
    restaurante_html = ''
    if ticket_data.get('restaurante_nombre'):
        restaurante_html = f"<p><strong>Restaurante:</strong> {ticket_data.get('restaurante_nombre')}</p>"
    
    prioridad = ticket_data.get('prioridad', 'media')
    prioridad_display = {
        'urgente': '🔴 URGENTE',
        'alta': '🟠 Alta',
        'media': '🔵 Media',
        'baja': '⚪ Baja'
    }.get(prioridad, prioridad.title())
    
    html = get_email_template('ticket_nuevo_admin',
        ticket_id=ticket_data.get('id'),
        nombre=ticket_data.get('nombre'),
        email=ticket_data.get('email'),
        telefono_html=telefono_html,
        tipo=ticket_data.get('tipo', 'consulta').replace('_', ' ').title(),
        prioridad=prioridad,
        prioridad_display=prioridad_display,
        restaurante_html=restaurante_html,
        asunto=ticket_data.get('asunto'),
        mensaje=ticket_data.get('mensaje'),
        admin_url=admin_url
    )
    
    return send_email(
        subject=f"🚨 Nuevo Ticket #{ticket_data.get('id')}: {ticket_data.get('asunto')[:50]}",
        recipients=admin_email,
        html_body=html
    )


def enviar_respuesta_ticket(ticket_data, respuesta):
    """
    Envía la respuesta de un ticket al usuario.
    
    Args:
        ticket_data: dict con datos del ticket original
        respuesta: texto de la respuesta
    """
    mensaje_original_html = ''
    if ticket_data.get('mensaje'):
        mensaje_original_html = f"""
        <div class="info-box" style="margin-top: 20px;">
            <p><strong>📝 Tu mensaje original:</strong></p>
            <p style="white-space: pre-wrap; color: #666;">{ticket_data.get('mensaje')}</p>
        </div>
        """
    
    html = get_email_template('ticket_respuesta',
        nombre=ticket_data.get('nombre', 'Usuario'),
        ticket_id=ticket_data.get('id'),
        asunto=ticket_data.get('asunto'),
        respuesta=respuesta,
        mensaje_original_html=mensaje_original_html
    )
    
    return send_email(
        subject=f"[Ticket #{ticket_data.get('id')}] Respuesta: {ticket_data.get('asunto')[:40]}",
        recipients=ticket_data.get('email'),
        html_body=html
    )


def enviar_email_recuperacion(usuario_data, reset_url):
    """
    Envía email de recuperación de contraseña.
    
    Args:
        usuario_data: dict con nombre y email
        reset_url: URL para restablecer contraseña
    """
    html = get_email_template('password_reset',
        nombre=usuario_data.get('nombre', 'Usuario'),
        reset_url=reset_url
    )
    
    return send_email(
        subject="Recuperar contraseña - Menú Digital",
        recipients=usuario_data.get('email'),
        html_body=html
    )
