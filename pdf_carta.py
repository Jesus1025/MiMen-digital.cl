"""PDF de la carta con ReportLab (Python puro: no necesita wkhtmltopdf ni un navegador)."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _pesos(valor):
    try:
        return '$' + f'{round(float(valor)):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return ''


def _color(hex_color, defecto):
    try:
        return colors.HexColor(hex_color) if hex_color else defecto
    except Exception:
        return defecto


def generar_pdf_carta(restaurante, menu, url_carta='', logo_path=None):
    """Devuelve los bytes de un PDF A4 con la carta del local, lista para imprimir."""
    acento = _color(restaurante.get('color_primario'), colors.HexColor('#9b2c1f'))
    tinta, suave, linea = colors.HexColor('#1d1b18'), colors.HexColor('#6f6a62'), colors.HexColor('#e6e0d6')
    mostrar_precios = restaurante.get('mostrar_precios') != 0
    mostrar_desc = restaurante.get('mostrar_descripciones') != 0

    st = {
        'titulo': ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=28, leading=32, alignment=TA_CENTER, textColor=tinta),
        'lema': ParagraphStyle('l', fontName='Helvetica', fontSize=12, leading=16, alignment=TA_CENTER, textColor=suave),
        'dato': ParagraphStyle('d', fontName='Helvetica', fontSize=9.5, leading=13, alignment=TA_CENTER, textColor=suave),
        'cat': ParagraphStyle('c', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=acento),
        'bajada': ParagraphStyle('b', fontName='Helvetica-Oblique', fontSize=9.5, leading=12, textColor=suave),
        'plato': ParagraphStyle('p', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=tinta),
        'desc': ParagraphStyle('ds', fontName='Helvetica', fontSize=9, leading=12, textColor=suave),
        'marca': ParagraphStyle('m', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=acento),
        'qr': ParagraphStyle('q', fontName='Helvetica', fontSize=9.5, leading=13, alignment=TA_CENTER, textColor=suave),
        'precio': ParagraphStyle('pr', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=tinta, alignment=2),
    }

    historia = []
    if logo_path:
        try:
            from reportlab.lib.utils import ImageReader
            iw, ih = ImageReader(logo_path).getSize()
            alto = 26 * mm
            logo = Image(logo_path, width=alto * iw / ih, height=alto)
            logo.hAlign = 'CENTER'
            historia += [logo, Spacer(1, 6)]
        except Exception:
            pass  # sin logo legible, la carta sale igual
    historia.append(Paragraph(escape(restaurante.get('nombre') or 'Carta'), st['titulo']))
    if restaurante.get('slogan'):
        historia += [Spacer(1, 4), Paragraph(escape(restaurante['slogan']), st['lema'])]
    datos = ' · '.join(escape(x) for x in (restaurante.get('direccion'), restaurante.get('telefono')) if x)
    if datos:
        historia += [Spacer(1, 6), Paragraph(datos, st['dato'])]
    historia.append(Spacer(1, 14))

    ancho = A4[0] - 36 * mm
    for categoria in menu:
        platos = categoria.get('platos') or []
        if not platos:
            continue
        cabeza = [Paragraph(escape(categoria.get('nombre') or ''), st['cat'])]
        if categoria.get('descripcion'):
            cabeza.append(Paragraph(escape(categoria['descripcion']), st['bajada']))
        filas = []
        for p in platos:
            izquierda = [Paragraph(escape(p.get('nombre') or ''), st['plato'])]
            if mostrar_desc and p.get('descripcion'):
                izquierda.append(Paragraph(escape(p['descripcion']), st['desc']))
            marcas = [n for c, n in (('es_nuevo', 'Nuevo'), ('es_vegano', 'Vegano'), ('es_vegetariano', 'Vegetariano'),
                                     ('es_sin_gluten', 'Sin gluten'), ('es_picante', 'Picante')) if p.get(c)]
            if marcas and 'Vegano' in marcas and 'Vegetariano' in marcas:
                marcas.remove('Vegetariano')
            marcas += [e for e in (p.get('etiquetas') or []) if isinstance(e, str) and e.strip()]
            if marcas:
                izquierda.append(Paragraph(' · '.join(escape(m) for m in marcas), st['marca']))
            precio = ''
            if mostrar_precios:
                if p.get('precio_oferta'):
                    precio = f'<strike><font size="8" color="#6f6a62">{_pesos(p.get("precio"))}</font></strike> {_pesos(p["precio_oferta"])}'
                else:
                    precio = _pesos(p.get('precio'))
            filas.append([izquierda, Paragraph(precio, st['precio'])])
        tabla = Table(filas, colWidths=[ancho - 32 * mm, 32 * mm])
        tabla.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, linea),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        # El título de la categoría nunca queda solo al final de una página
        historia.append(KeepTogether(cabeza + [Spacer(1, 4), tabla] if len(filas) <= 6 else cabeza + [Spacer(1, 4)]))
        if len(filas) > 6:
            historia.append(tabla)
        historia.append(Spacer(1, 12))

    if url_carta:
        qr = QrCodeWidget(url_carta)
        x1, y1, x2, y2 = qr.getBounds()
        lado = 34 * mm
        dib = Drawing(lado, lado, transform=[lado / (x2 - x1), 0, 0, lado / (y2 - y1), 0, 0])
        dib.add(qr)
        dib.hAlign = 'CENTER'
        historia.append(KeepTogether([Spacer(1, 6), dib, Paragraph('Escanea para ver la carta digital con fotos', st['qr'])]))

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(acento)
        canvas.setLineWidth(2)
        canvas.line(18 * mm, A4[1] - 12 * mm, A4[0] - 18 * mm, A4[1] - 12 * mm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(suave)
        texto = f'Página {doc.page}'
        if url_carta:
            texto = f'Carta digital: {url_carta}   ·   ' + texto
        canvas.drawCentredString(A4[0] / 2, 10 * mm, texto)
        canvas.restoreState()

    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"Carta {restaurante.get('nombre') or ''}", author='MiMenú · Divergent Studio')
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()
