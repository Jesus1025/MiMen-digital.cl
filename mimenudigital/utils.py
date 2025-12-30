"""
utils.py

Helpers extraídos de app_menu.py para mejorar organización.
"""
import os
from datetime import date
import logging

logger = logging.getLogger(__name__)


def dict_from_row(row):
    return dict(row) if row else None


def list_from_rows(rows):
    return [dict(row) for row in rows] if rows else []


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename, allowed=ALLOWED_EXTENSIONS):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed


def generar_qr_restaurante(url, filename, base_dir=os.path.dirname(os.path.abspath(__file__))):
    qr_folder = os.path.join(base_dir, 'static', 'uploads', 'qrs')
    os.makedirs(qr_folder, exist_ok=True)
    qr_path = os.path.join(qr_folder, filename)

    if os.path.exists(qr_path):
        logger.debug(f"QR already exists: {qr_path}")
        return qr_path

    try:
        import qrcode
    except ImportError as e:
        logger.error('qrcode module not available')
        raise RuntimeError('QR generation unavailable: install qrcode[pil]') from e

    try:
        logger.info(f"Generating QR code for: {url}")
        img = qrcode.make(url)
        img.save(qr_path)
        logger.info(f"QR code saved: {qr_path}")
        return qr_path
    except Exception as e:
        logger.error(f'Failed to generate QR for {url}: {e}')
        raise


def registrar_visita(restaurante_id, req, get_db):
    """Registra visita en BD usando la conexión proporcionada por get_db().
    get_db es pasado para evitar import cycles.
    """
    try:
        db = get_db()
        with db.cursor() as cur:
            ip_address = req.headers.get('X-Forwarded-For', req.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()[:45]
            user_agent = req.headers.get('User-Agent', '')[:500]
            referer = req.headers.get('Referer', '')[:500]
            es_movil = any(x in user_agent.lower() for x in ['mobile', 'android', 'iphone', 'ipad'])
            es_qr = 'qr' in (referer or '').lower() or req.args.get('qr') == '1'

            cur.execute('''
                INSERT INTO visitas 
                (restaurante_id, ip_address, user_agent, referer, es_movil, es_qr, fecha)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ''', (restaurante_id, ip_address, user_agent, referer, 1 if es_movil else 0, 1 if es_qr else 0))

            hoy = date.today().isoformat()
            cur.execute('''
                INSERT INTO estadisticas_diarias 
                (restaurante_id, fecha, visitas, escaneos_qr, visitas_movil, visitas_desktop)
                VALUES (%s, %s, 1, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    visitas = visitas + 1,
                    escaneos_qr = escaneos_qr + %s,
                    visitas_movil = visitas_movil + %s,
                    visitas_desktop = visitas_desktop + %s
            ''', (
                restaurante_id, hoy,
                1 if es_qr else 0,
                1 if es_movil else 0,
                0 if es_movil else 1,
                1 if es_qr else 0,
                1 if es_movil else 0,
                0 if es_movil else 1
            ))

            db.commit()

    except Exception as e:
        logger.error(f"Error registrando visita: {e}")
        try:
            db.rollback()
        except Exception:
            pass
