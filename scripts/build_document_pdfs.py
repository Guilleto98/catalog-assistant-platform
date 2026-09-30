#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = A4
NAVY = colors.HexColor("#102A43")
NAVY_2 = colors.HexColor("#243B53")
TEAL = colors.HexColor("#087F8C")
TEAL_LIGHT = colors.HexColor("#DDF4F5")
BLUE = colors.HexColor("#2F6FB3")
BLUE_LIGHT = colors.HexColor("#E7F0FA")
GOLD = colors.HexColor("#D6A84B")
GOLD_LIGHT = colors.HexColor("#FFF5DC")
GREEN = colors.HexColor("#4F8A5B")
GREEN_LIGHT = colors.HexColor("#E7F3E8")
PURPLE = colors.HexColor("#7253A6")
PURPLE_LIGHT = colors.HexColor("#EFE9F8")
RED = colors.HexColor("#B94444")
RED_LIGHT = colors.HexColor("#F9E6E6")
INK = colors.HexColor("#243B53")
MUTED = colors.HexColor("#627D98")
LINE = colors.HexColor("#BCCCDC")
PAPER = colors.HexColor("#F7F9FC")
WHITE = colors.white


def register_fonts():
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    regular = candidates[0] if candidates[0].exists() else candidates[2]
    bold = candidates[1] if candidates[1].exists() else candidates[3]
    pdfmetrics.registerFont(TTFont("DocSans", str(regular)))
    pdfmetrics.registerFont(TTFont("DocSans-Bold", str(bold)))


register_fonts()


def styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", fontName="DocSans-Bold", fontSize=28, leading=32,
            textColor=WHITE, alignment=TA_LEFT, spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", fontName="DocSans", fontSize=13, leading=18,
            textColor=colors.HexColor("#D9E2EC"), spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "H1", fontName="DocSans-Bold", fontSize=18, leading=22,
            textColor=NAVY, spaceBefore=8, spaceAfter=10, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", fontName="DocSans-Bold", fontSize=13.5, leading=17,
            textColor=TEAL, spaceBefore=10, spaceAfter=7, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3", fontName="DocSans-Bold", fontSize=11.2, leading=14,
            textColor=BLUE, spaceBefore=8, spaceAfter=5, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", fontName="DocSans", fontSize=9.6, leading=14,
            textColor=INK, spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small", fontName="DocSans", fontSize=8, leading=10.5,
            textColor=MUTED,
        ),
        "bullet": ParagraphStyle(
            "Bullet", fontName="DocSans", fontSize=9.3, leading=13,
            textColor=INK, leftIndent=13, firstLineIndent=-8, spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout", fontName="DocSans-Bold", fontSize=11, leading=15,
            textColor=NAVY, spaceAfter=0,
        ),
        "table": ParagraphStyle(
            "Table", fontName="DocSans", fontSize=7.4, leading=9.2,
            textColor=INK,
        ),
        "table_bold": ParagraphStyle(
            "TableBold", fontName="DocSans-Bold", fontSize=7.4, leading=9.2,
            textColor=INK,
        ),
        "code": ParagraphStyle(
            "Code", fontName="Courier", fontSize=7.5, leading=10,
            textColor=NAVY,
        ),
        "diagram_title": ParagraphStyle(
            "DiagramTitle", fontName="DocSans-Bold", fontSize=10.5, leading=13,
            textColor=NAVY, alignment=TA_CENTER, spaceAfter=6,
        ),
    }


S = styles()


class NumberedDocTemplate(BaseDocTemplate):
    def __init__(self, filename, title, **kwargs):
        self.document_title = title
        super().__init__(filename, **kwargs)
        frame = Frame(18 * mm, 17 * mm, PAGE_W - 36 * mm, PAGE_H - 34 * mm, id="normal")
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self._decorate))

    def _decorate(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, PAGE_H - 13 * mm, PAGE_W - 18 * mm, PAGE_H - 13 * mm)
        canvas.setFont("DocSans", 7.3)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, PAGE_H - 10 * mm, self.document_title)
        canvas.drawRightString(PAGE_W - 18 * mm, 10 * mm, f"Solvo  |  {doc.page}")
        canvas.restoreState()


def p(text, style="body"):
    return Paragraph(text, S[style])


def bullet(text):
    return Paragraph(f"• {text}", S["bullet"])


def section_title(number, title):
    return [Spacer(1, 3 * mm), p(f"{number}. {title}", "h1"), HRFlowable(width="100%", thickness=1.4, color=TEAL, spaceAfter=8)]


def callout(text, bg=TEAL_LIGHT, stripe=TEAL):
    t = Table([[p(text, "callout")]], colWidths=[PAGE_W - 42 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#C8D9E5")),
        ("LINEBEFORE", (0, 0), (0, -1), 5, stripe),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def cover(title, subtitle, label, accent=TEAL):
    story = []
    canvas_box = Table([
        [p(label.upper(), "small")],
        [Spacer(1, 13 * mm)],
        [p(title, "title")],
        [p(subtitle, "subtitle")],
        [Spacer(1, 63 * mm)],
        [p("Proyecto de agente conversacional y plataforma de tools", "subtitle")],
        [p("Agosto 2026", "subtitle")],
    ], colWidths=[PAGE_W - 36 * mm])
    canvas_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
        ("LEFTPADDING", (0, 0), (-1, -1), 16 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ("LINEBEFORE", (0, 0), (0, -1), 8, accent),
    ]))
    story.extend([canvas_box, PageBreak()])
    return story


def para_cell(value, bold=False):
    if isinstance(value, Paragraph):
        return value
    return p(str(value), "table_bold" if bold else "table")


def data_table(headers, rows, widths, header_color=NAVY, font_size=None):
    data = [[para_cell(h, True) for h in headers]]
    for row in rows:
        data.append([para_cell(v) for v in row])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            commands.append(("BACKGROUND", (0, i), (-1, i), PAPER))
    t.setStyle(TableStyle(commands))
    return t


def arrow(d, x1, y1, x2, y2, color=NAVY_2, width=1.2):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    size = 5
    pts = [
        x2, y2,
        x2 - size * math.cos(a - 0.55), y2 - size * math.sin(a - 0.55),
        x2 - size * math.cos(a + 0.55), y2 - size * math.sin(a + 0.55),
    ]
    d.add(Polygon(pts, fillColor=color, strokeColor=color))


def box(d, x, y, w, h, text, fill=BLUE_LIGHT, stroke=BLUE, font=8.2, radius=6):
    d.add(Rect(x, y, w, h, rx=radius, ry=radius, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    lines = text.split("\n")
    total = len(lines) * (font + 2)
    start_y = y + h / 2 + total / 2 - font
    for i, line in enumerate(lines):
        d.add(String(x + w / 2, start_y - i * (font + 2), line, fontName="DocSans-Bold", fontSize=font, fillColor=INK, textAnchor="middle"))


def captioned_drawing(title, drawing):
    return KeepTogether([p(title, "diagram_title"), drawing, Spacer(1, 3 * mm)])


def diagram_general():
    d = Drawing(480, 245)
    box(d, 12, 99, 95, 46, "Aplicación\nAngular", PURPLE_LIGHT, PURPLE)
    box(d, 135, 99, 100, 46, "Agente\nconversacional", TEAL_LIGHT, TEAL)
    arrow(d, 107, 122, 135, 122)
    ys = [190, 135, 80, 25]
    labels = ["Resolución de códigos\ny entidades", "Consultas\ny análisis", "Archivos\ny reportes", "Acciones\ncontroladas"]
    fills = [BLUE_LIGHT, GREEN_LIGHT, GOLD_LIGHT, RED_LIGHT]
    strokes = [BLUE, GREEN, GOLD, RED]
    for y, label, fill, stroke in zip(ys, labels, fills, strokes):
        box(d, 270, y, 125, 38, label, fill, stroke, font=7.5)
        arrow(d, 235, 122, 270, y + 19, color=stroke)
        if "Acciones" in label:
            box(d, 405, y, 68, 38, "Validar y\nconfirmar", RED_LIGHT, RED, font=7)
            arrow(d, 395, y + 19, 405, y + 19, color=RED)
            arrow(d, 473, y + 19, 473, 122, color=RED)
        else:
            arrow(d, 395, y + 19, 448, 122, color=stroke)
    box(d, 420, 99, 58, 46, "API\nCliente", BLUE_LIGHT, NAVY)
    box(d, 365, 170, 110, 38, "JWT, roles y\nestablecimientos", GOLD_LIGHT, GOLD, font=7.2)
    arrow(d, 449, 145, 420, 170, color=GOLD)
    return d


def diagram_purchase():
    d = Drawing(480, 365)
    box(d, 170, 322, 140, 38, "Orden de compra\nde hacienda", PURPLE_LIGHT, PURPLE)

    # Four independent dependency lanes keep the full model readable without
    # crossing arrows. Each lane expands one direct branch of the root order.
    lanes = [
        (8, 82, "LÍNEAS", ["Líneas de la orden"]),
        (98, 102, "SANIDAD", ["Inspección sanitaria", "↓", "Caravanas y archivos"]),
        (208, 152, "RECEPCIÓN Y FLETE", [
            "Orden de recepción", "↓", "Líneas de recepción", "", "Orden de flete",
            "↓", "Líneas de flete", "↓", "Viajes", "↓", "Líneas del viaje", "",
            "Recepción física", "↓", "Archivos de caravanas", "Caravanas recibidas",
        ]),
        (368, 104, "LIQUIDACIÓN", [
            "Liquidación de hacienda", "↓", "Líneas y animales", "",
            "Órdenes de facturación", "↓", "Integración ERP",
        ]),
    ]
    lane_top = 278
    lane_bottom = 18
    for idx, (x, w, title, items) in enumerate(lanes):
        stroke = [BLUE, GREEN, TEAL, GOLD][idx]
        fill = [BLUE_LIGHT, GREEN_LIGHT, TEAL_LIGHT, GOLD_LIGHT][idx]
        d.add(Rect(x, lane_bottom, w, lane_top-lane_bottom, rx=7, ry=7,
                   fillColor=colors.HexColor("#FAFCFE"), strokeColor=stroke, strokeWidth=1))
        d.add(Rect(x, lane_top-30, w, 30, rx=7, ry=7,
                   fillColor=fill, strokeColor=stroke, strokeWidth=1))
        d.add(String(x+w/2, lane_top-19, title, fontName="DocSans-Bold",
                     fontSize=6.5 if w < 110 else 6.8, fillColor=INK, textAnchor="middle"))
        arrow(d, 240, 322, x+w/2, lane_top, color=stroke)

        usable_top = lane_top - 48
        step = 12.5 if idx == 2 else 23
        for j, item in enumerate(items):
            if not item:
                continue
            y = usable_top - j * step
            if item == "↓":
                d.add(String(x+w/2, y+2, "↓", fontName="DocSans-Bold", fontSize=8,
                             fillColor=stroke, textAnchor="middle"))
            else:
                d.add(String(x+w/2, y, item, fontName="DocSans-Bold",
                             fontSize=6.2 if idx == 2 else 6.5,
                             fillColor=INK, textAnchor="middle"))
    return d


def diagram_supply():
    d = Drawing(480, 210)
    box(d, 15, 145, 115, 40, "Orden de compra\nde insumos", PURPLE_LIGHT, PURPLE)
    box(d, 170, 145, 100, 40, "Líneas", BLUE_LIGHT, BLUE)
    box(d, 170, 75, 110, 40, "Recepción\nde insumos", GREEN_LIGHT, GREEN)
    box(d, 330, 75, 110, 40, "Liquidación\nde insumos", GOLD_LIGHT, GOLD)
    box(d, 180, 12, 92, 36, "Líneas de\nrecepción", BLUE_LIGHT, BLUE, font=7.2)
    box(d, 340, 12, 92, 36, "Líneas de\nliquidación", BLUE_LIGHT, BLUE, font=7.2)
    box(d, 15, 12, 105, 36, "Integración ERP", RED_LIGHT, RED, font=7.2)
    arrow(d, 130, 165, 170, 165)
    arrow(d, 72, 145, 225, 115)
    arrow(d, 280, 95, 330, 95)
    arrow(d, 225, 75, 226, 48)
    arrow(d, 385, 75, 386, 48)
    arrow(d, 170, 88, 120, 30, color=RED)
    arrow(d, 330, 88, 120, 30, color=RED)
    return d


def diagram_livestock():
    d = Drawing(480, 245)
    box(d, 20, 170, 85, 42, "Animal", PURPLE_LIGHT, PURPLE)
    box(d, 155, 195, 95, 38, "Transacciones", BLUE_LIGHT, BLUE)
    box(d, 155, 140, 95, 38, "Caravana", BLUE_LIGHT, BLUE)
    arrow(d, 105, 191, 155, 214)
    arrow(d, 105, 191, 155, 159)
    box(d, 20, 65, 110, 42, "Operación por lote", GREEN_LIGHT, GREEN)
    labels = ["Entradas", "Salidas y bajas", "Pesajes", "Aplicaciones\nsanitarias", "Asignación\nde lote", "Auditoría\ny reversión"]
    positions = [(165, 95), (270, 95), (375, 95), (165, 35), (270, 35), (375, 35)]
    for label, (x, y) in zip(labels, positions):
        box(d, x, y, 88, 34, label, GREEN_LIGHT, GREEN, font=6.8)
        arrow(d, 130, 86, x, y + 17, color=GREEN)
    box(d, 20, 5, 110, 34, "Archivo bastón / SNIG", GOLD_LIGHT, GOLD, font=7)
    box(d, 165, 5, 100, 34, "Filtro o comparación", GOLD_LIGHT, GOLD, font=7)
    arrow(d, 130, 22, 165, 22, color=GOLD)
    return d


def diagram_current_architecture():
    d = Drawing(480, 260)
    box(d, 12, 180, 120, 42, "SecurityAdmin\nFrontEnd", BLUE_LIGHT, BLUE)
    box(d, 12, 105, 120, 42, "SecurityAdmin\nBackEnd", BLUE_LIGHT, BLUE)
    arrow(d, 72, 180, 72, 147)
    d.add(Rect(175, 145, 290, 100, rx=10, ry=10, fillColor=PURPLE_LIGHT, strokeColor=PURPLE, strokeWidth=1.2))
    d.add(String(320, 225, "AgroLink FrontEnd", fontName="DocSans-Bold", fontSize=10, fillColor=PURPLE, textAnchor="middle"))
    for i, label in enumerate(["Caravanas", "Insumos", "Hacienda"]):
        box(d, 195 + i*85, 165, 72, 32, label, colors.HexColor("#E4D7F4"), PURPLE, font=6.8)
    d.add(Rect(175, 20, 290, 100, rx=10, ry=10, fillColor=GREEN_LIGHT, strokeColor=GREEN, strokeWidth=1.2))
    d.add(String(320, 100, "AgroLink BackEnd", fontName="DocSans-Bold", fontSize=10, fillColor=GREEN, textAnchor="middle"))
    for i, label in enumerate(["Caravanas", "Insumos", "Hacienda", "Fletes"]):
        x = 190 + (i % 3) * 85
        y = 55 if i < 3 else 25
        box(d, x, y, 72, 28, label, colors.HexColor("#D9ECD9"), GREEN, font=6.5)
    box(d, 12, 30, 120, 42, "ERP PSIG /\nWinCampo", GOLD_LIGHT, GOLD)
    arrow(d, 132, 51, 175, 51, color=GOLD)
    arrow(d, 132, 126, 175, 90)
    arrow(d, 320, 145, 320, 120)
    box(d, 365, 205, 82, 28, "AWS / Cloudflare", GOLD_LIGHT, GOLD, font=6.8)
    return d


def diagram_target_architecture():
    d = Drawing(480, 315)
    box(d, 10, 245, 100, 42, "Usuario\nautenticado", PURPLE_LIGHT, PURPLE)
    box(d, 145, 245, 130, 42, "AgroLink Frontend +\ncomponente Angular", PURPLE_LIGHT, PURPLE, font=7.2)
    box(d, 320, 245, 145, 42, "API Gateway\ndel agente", TEAL_LIGHT, TEAL)
    arrow(d, 110, 266, 145, 266)
    arrow(d, 275, 266, 320, 266)
    d.add(String(298, 276, "HTTPS + JWT", fontName="DocSans", fontSize=6.4, fillColor=MUTED, textAnchor="middle"))
    d.add(Rect(65, 40, 390, 165, rx=10, ry=10, fillColor=PAPER, strokeColor=LINE, strokeWidth=1))
    d.add(String(260, 188, "Infraestructura del cliente de Solvo", fontName="DocSans-Bold", fontSize=10, fillColor=NAVY, textAnchor="middle"))
    box(d, 85, 125, 105, 38, "SecurityAdmin\nAPI", BLUE_LIGHT, BLUE)
    box(d, 220, 125, 120, 38, "Orquestador privado\n/ n8n", GREEN_LIGHT, GREEN, font=7.2)
    box(d, 365, 125, 70, 38, "AgroLink\nREST API", BLUE_LIGHT, NAVY, font=7.2)
    box(d, 85, 65, 105, 38, "PostgreSQL\ndel agente", GOLD_LIGHT, GOLD)
    box(d, 220, 65, 120, 38, "Archivos temporales\n/ almacenamiento", GOLD_LIGHT, GOLD, font=6.8)
    box(d, 365, 65, 70, 38, "Backoffice\nprivado", RED_LIGHT, RED, font=7)
    arrow(d, 392, 245, 138, 163, color=BLUE)
    arrow(d, 392, 245, 280, 163, color=GREEN)
    arrow(d, 340, 144, 365, 144)
    arrow(d, 280, 125, 138, 103, color=GOLD)
    arrow(d, 280, 125, 280, 103, color=GOLD)
    arrow(d, 400, 103, 400, 125, color=RED)
    box(d, 10, 5, 120, 30, "Proveedor LLM /\nmodelo privado", PURPLE_LIGHT, PURPLE, font=6.7)
    arrow(d, 220, 125, 130, 28, color=PURPLE)
    box(d, 350, 5, 105, 30, "Solvo por VPN", BLUE_LIGHT, BLUE, font=7)
    arrow(d, 402, 35, 400, 65, color=BLUE)
    return d


def diagram_auth_sequence():
    d = Drawing(480, 350)
    actors = [(35, "Usuario"), (120, "AgroLink\nFrontend"), (220, "API Gateway"), (310, "SecurityAdmin"), (390, "Orquestador"), (455, "AgroLink\nAPI")]
    for x, label in actors:
        box(d, x-32, 306, 64, 32, label, BLUE_LIGHT, BLUE, font=6.5, radius=3)
        d.add(Line(x, 306, x, 20, strokeColor=LINE, strokeWidth=0.7, strokeDashArray=[3, 3]))
    events = [
        (285, 35, 120, "Inicia sesión"),
        (260, 120, 310, "Usuario + contraseña"),
        (235, 310, 120, "JWT de sesión"),
        (205, 35, 120, "Consulta al agente"),
        (180, 120, 220, "Mensaje + conversation_id + JWT"),
        (155, 220, 310, "Validar token"),
        (130, 310, 220, "Identidad + claims"),
        (105, 220, 390, "Solicitud normalizada + token"),
        (80, 390, 455, "Tool request + JWT usuario"),
        (55, 455, 390, "Datos o 401/403"),
        (30, 390, 220, "Resultado estructurado"),
    ]
    for y, x1, x2, text in events:
        arrow(d, x1, y, x2, y, color=TEAL if x2 > x1 else NAVY_2, width=1)
        d.add(String((x1+x2)/2, y+4, text, fontName="DocSans", fontSize=5.6, fillColor=INK, textAnchor="middle"))
    return d


def build_catalog():
    path = OUT / "catalogo-tools-propuesto.pdf"
    doc = NumberedDocTemplate(str(path), "Catálogo de tools propuesto", pagesize=A4,
                              leftMargin=18*mm, rightMargin=18*mm, topMargin=17*mm, bottomMargin=17*mm)
    story = cover("Catálogo de tools\npropuesto", "Segmentación funcional de la API REST para el agente conversacional", "Documento técnico 01", TEAL)
    story += section_title(1, "Decisión de arquitectura")
    story.append(callout("La API contiene 214 operaciones, pero el agente no debe recibir 214 herramientas independientes."))
    story.append(Spacer(1, 5*mm))
    for text in [
        "Mantener un registro interno que conozca todas las operaciones.",
        "Exponer tools funcionales con contratos reducidos y estables.",
        "Cargar herramientas dinámicamente por módulo, pantalla, rol y etapa del flujo.",
        "Mantener entre 10 y 15 tools visibles simultáneamente al modelo.",
        "Separar de forma absoluta consultas, archivos y mutaciones.",
    ]: story.append(bullet(text))
    story.append(Spacer(1, 5*mm))
    story.append(captioned_drawing("Principio de exposición", diagram_general()))
    story.append(PageBreak())

    groups = [
        ("2", "Grupo A - Contexto y resolución", [
            ("resolve_code_types", "GET /codetypes, GET /codetypes/{id}", "R0", "MVP"),
            ("resolve_codes", "GET /codes, GET /codes/{id}", "R0", "MVP"),
            ("search_audit_events", "GET /audit y endpoints /audit por entidad", "R0", "MVP"),
            ("list_related_files", "GET /files y listados de adjuntos/caravan files", "R1", "MVP"),
            ("list_user_marks", "GET /marks", "R0", "Opcional"),
        ]),
        ("3", "Grupo B - Ganado", [
            ("search_livestock", "GET /livestock", "R0", "MVP"),
            ("get_livestock_detail", "GET /livestock/{id}", "R0", "MVP"),
            ("get_livestock_movements", "GET /livestock/{id}/transactions y detalle", "R0", "MVP"),
            ("get_livestock_batch_history", "GET /livestock/batchtransactions y detalle", "R0", "MVP"),
            ("search_livestock_batches", "GET /livestockbatch", "R0", "MVP"),
            ("search_livestock_audit", "GET /livestock/audit", "R0", "MVP"),
            ("compare_livestock_file", "POST /livestock/filterbyfile, POST /livestock/snigcompare", "R2-R3", "Fase 2"),
        ]),
        ("4", "Grupo C - Compra de hacienda", [
            ("search_livestock_purchase_orders", "GET /livestockpurchaseorders", "R0", "MVP"),
            ("get_livestock_purchase_order", "Detalle, estado, líneas, caravanas y adjuntos", "R0-R1", "MVP"),
            ("check_livestock_purchase_traceability", "GET .../traceabilitycheck", "R0", "MVP"),
            ("generate_livestock_trace_report", "POST .../tracereport", "R1", "MVP"),
            ("get_livestock_order_health_inspection", "Inspección, caravanas y archivos relacionados", "R0-R1", "MVP"),
            ("search_livestock_receiving_orders", "GET /livestockreceivingorders y lista anidada", "R0", "MVP"),
            ("get_livestock_receiving_order", "Detalle y líneas de recepción", "R0", "MVP"),
            ("search_livestock_freight_orders", "GET /livestockfreightorders y lista anidada", "R0", "MVP"),
            ("get_livestock_freight_order", "Detalle, líneas y auditoría", "R0", "MVP"),
            ("search_livestock_trips", "GET /livestockfreighttrips y lista anidada", "R0", "MVP"),
            ("get_livestock_trip", "Detalle, líneas y auditoría", "R0", "MVP"),
            ("get_livestock_receiving", "Resumen, archivos y caravanas recibidas", "R0-R1", "MVP"),
            ("get_livestock_settlement", "Liquidación, líneas, animales y distribución de pesos", "R0", "MVP"),
            ("get_livestock_billing_orders", "Órdenes de facturación y líneas", "R0", "Fase 2"),
        ]),
        ("5", "Grupo D - Compra de insumos", [
            ("search_supply_purchase_orders", "GET /supplypurchaseorders", "R0", "MVP"),
            ("get_supply_purchase_order", "Detalle, líneas y auditoría", "R0", "MVP"),
            ("search_supply_receivings", "GET /supplyreceivings y líneas consolidadas", "R0", "MVP"),
            ("get_supply_receiving", "Detalle, líneas y auditoría", "R0", "MVP"),
            ("search_supply_settlements", "GET /supplysettlement", "R0", "MVP"),
            ("get_supply_settlement", "Detalle, líneas y auditoría", "R0", "MVP"),
        ]),
        ("6", "Grupo E - Analítica", [
            ("get_establishment_rankings", "GET /establishmentsrankings", "R0", "MVP"),
            ("get_establishment_statistics", "GET /establishmentsstatics y detalle", "R0", "MVP"),
            ("compare_establishment_periods", "GET /establishmentsstaticscompare", "R0", "MVP"),
            ("get_livestock_cost_analytics", "Waterfall, evolución y distribuciones de compra", "R0", "MVP"),
            ("get_livestock_purchase_ranking", "GET /livestockpurchasesranking", "R0", "MVP"),
            ("get_acg_quotations", "Lista, semana y detalle de cotizaciones", "R0", "MVP"),
            ("calculate_livestock_margin_projection", "Proyección y valores por defecto", "R0", "MVP"),
            ("search_health_inspections", "GET /healthinspections", "R0-R1", "MVP"),
        ]),
    ]
    for number, title, rows in groups:
        story += section_title(number, title)
        story.append(data_table(["Tool", "Endpoints principales", "Riesgo", "Fase"], rows,
                                [62*mm, 83*mm, 18*mm, 22*mm], TEAL))
        story.append(Spacer(1, 4*mm))

    story.append(PageBreak())
    story += section_title(7, "Grupo F - Acciones futuras")
    story.append(p("Las mutaciones deben diseñarse después de validar las reglas de negocio. No se recomienda una tool genérica <font name='DocSans-Bold'>execute_api_operation</font>."))
    future = [
        "create_or_update_livestock", "register_livestock_batch_movement", "manage_livestock_purchase_order",
        "manage_livestock_receiving_order", "manage_livestock_freight_order", "manage_livestock_trip",
        "manage_livestock_settlement", "manage_supply_purchase_order", "manage_supply_receiving",
        "manage_supply_settlement", "manage_acg_quotation", "manage_user_mark", "upload_related_file",
    ]
    rows = [[future[i], future[i+1] if i+1 < len(future) else ""] for i in range(0, len(future), 2)]
    story.append(data_table(["Familia candidata", "Familia candidata"], rows, [92*mm, 92*mm], PURPLE))
    story.append(Spacer(1, 5*mm))
    story.append(callout("Cada tool de escritura debe aceptar solo los campos necesarios, recuperar el estado actual, validar la transición, presentar un resumen y solicitar confirmación antes de ejecutar.", GOLD_LIGHT, GOLD))

    story += section_title(8, "Operaciones excluidas inicialmente")
    excluded = [
        "Los 23 endpoints DELETE.", "Reversión de auditoría de ganado.", "Integración y reversión de integración ERP.",
        "Cambios de estado sin una máquina de estados documentada.", "Importación masiva general.",
        "Bajas y actualizaciones masivas de animales.", "División y reagrupación de líneas de liquidación.",
    ]
    for item in excluded: story.append(bullet(item))

    story += section_title(9, "Contrato común de salida")
    code = '''{
  "status": "ok | needs_clarification | denied | error",
  "operation": "nombre_funcional",
  "filters": {},
  "data": [],
  "pagination": {"skip": 0, "take": 50, "hasMore": false},
  "source": {"endpoint": "GET /ruta", "timestamp": "ISO-8601"},
  "warnings": []
}'''
    code_table = Table([[Preformatted(code, S["code"])]], colWidths=[PAGE_W-42*mm])
    code_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#EDF2F7")), ("BOX", (0,0), (-1,-1), .5, LINE), ("LEFTPADDING", (0,0), (-1,-1), 10), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
    story.append(code_table)
    story.append(Spacer(1, 4*mm))
    story.append(p("El adaptador traduce errores HTTP a estados comprensibles sin filtrar detalles internos ni datos de otros usuarios."))
    doc.build(story)
    return path


def build_model():
    path = OUT / "modelo-funcional-y-dependencias.pdf"
    doc = NumberedDocTemplate(str(path), "Modelo funcional y dependencias", pagesize=A4,
                              leftMargin=18*mm, rightMargin=18*mm, topMargin=17*mm, bottomMargin=17*mm)
    story = cover("Modelo funcional\ny dependencias", "Procesos, relaciones de dominio y criterios de adaptación para el agente", "Documento técnico 02", PURPLE)
    story += section_title(1, "Vista general")
    story.append(p("La API expone dos cadenas transaccionales principales, un dominio operativo de animales y varios servicios transversales. Los tags de Swagger describen componentes técnicos; para el agente conviene pensar en procesos completos."))
    story.append(captioned_drawing("Del usuario a la API: capas funcionales del agente", diagram_general()))
    story.append(callout("El agente debe operar sobre intenciones completas: resolver, consultar, analizar, generar y actuar con control.", PURPLE_LIGHT, PURPLE))
    story.append(PageBreak())

    story += section_title(2, "Cadena de compra de hacienda")
    story.append(p("Es el proceso más profundo del contrato. No debe modelarse como una sola tool ni como endpoints aislados."))
    story.append(captioned_drawing("Dependencias de la orden de compra de hacienda", diagram_purchase()))
    story.append(p("Dependencias conversacionales importantes", "h2"))
    deps = [
        "La orden de compra es el identificador raíz para sanidad, recepción, flete, viajes, recepción física y liquidación.",
        "Fletes y viajes requieren identificadores anidados de orden de compra, orden de recepción y orden de flete.",
        "Las liquidaciones dependen de la compra y pueden generar órdenes de facturación e integración ERP.",
        "Los estados restringen qué entidades pueden modificarse; algunos impiden editar una inspección o una orden de recepción.",
    ]
    for x in deps: story.append(bullet(x))
    story.append(PageBreak())

    story += section_title(3, "Cadena de compra de insumos")
    story.append(captioned_drawing("Compra, recepción, liquidación e integración", diagram_supply()))
    story.append(p("La recepción conecta la orden de compra con la liquidación y con las integraciones ERP. Las tools deben conservar esta relación y no tratar cada entidad como una lista aislada."))
    story += section_title(4, "Ganado y movimientos")
    story.append(p("El recurso animal combina ficha actual, transacciones individuales, operaciones por lote, auditoría e importación mediante archivos."))
    story.append(captioned_drawing("Superficie funcional del recurso animal", diagram_livestock()))
    story.append(PageBreak())

    story += section_title(5, "Datos maestros")
    story.append(callout("Codes no es un módulo accesorio: resuelve establecimientos, categorías, edades, productores, consignatarios, intermediarios y otras entidades codificadas.", BLUE_LIGHT, BLUE))
    story.append(Spacer(1, 5*mm))
    seq = [
        "Interpretar el término escrito por el usuario.",
        "Consultar tipos de código y códigos aplicables.",
        "Devolver candidatos si existe ambigüedad.",
        "Conservar el identificador resuelto únicamente durante la operación o conversación autorizada.",
        "Enviar el identificador a la tool de negocio.",
    ]
    for i, x in enumerate(seq, 1): story.append(p(f"<font name='DocSans-Bold'>{i}.</font> {x}"))

    story += section_title(6, "Parámetros transversales")
    rows = [
        ("skip + take", "20 operaciones", "Paginación por desplazamiento; aplicar límites por defecto"),
        ("universalFilter", "14 operaciones", "Búsqueda textual general"),
        ("establishmentId", "14 operaciones", "Puede ser escalar o arreglo; normalizar"),
        ("sortBy", "13 operaciones", "Arreglo de criterios; restringir campos permitidos"),
        ("Fechas", "Varios nombres", "Unificar dateFrom/dateTo y startDate/endDate"),
        ("fileExport", "5 operaciones", "Separar datos y generación de archivo"),
    ]
    story.append(data_table(["Patrón", "Cobertura", "Tratamiento"], rows, [43*mm, 35*mm, 106*mm], TEAL))
    story.append(Spacer(1, 4*mm))
    story.append(callout("No hay máximos ni valores por defecto documentados para skip y take. Deben acordarse con el cliente de Solvo antes de habilitar consultas abiertas.", GOLD_LIGHT, GOLD))

    story += section_title(7, "Archivos y formatos")
    facts = [
        ("14", "operaciones multipart/form-data"), ("57", "operaciones application/json"),
        ("1", "respuesta PDF: informe de trazabilidad"), ("1", "respuesta text/plain: reversión de auditoría"),
    ]
    cards = []
    for n, label in facts:
        cards.append([p(f"<font size='17' color='#087F8C'><b>{n}</b></font><br/>{label}", "small")])
    ct = Table([cards], colWidths=[46*mm]*4)
    ct.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), PAPER), ("BOX", (0,0), (-1,-1), .4, LINE), ("INNERGRID", (0,0), (-1,-1), .4, LINE), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (0,0), (-1,-1), "CENTER"), ("TOPPADDING", (0,0), (-1,-1), 9), ("BOTTOMPADDING", (0,0), (-1,-1), 9)]))
    story.append(ct)
    story.append(Spacer(1, 4*mm))
    story.append(p("Las cargas incluyen movimientos masivos de ganado, archivos de bastón, comparación SNIG, adjuntos, archivos de inspección sanitaria, archivos de recepción e importación general."))

    story += section_title(8, "Modelos con mayor superficie")
    models = [
        ("LiveStockPurchaseOrderDTO", "58"), ("LivestockFreightTripDTO", "44"), ("CaravanDTO", "30"),
        ("LivestockPurchaseOrderHealthInspectionDTO", "29"), ("LivestockMarginProjectionDTO", "23"),
        ("LivestockFreightOrderDTO", "21"), ("LivestockPurchaseSettlementBillingOrderDTO", "21"),
        ("SupplyPurchaseSettlementDTO", "21"),
    ]
    story.append(data_table(["Schema", "Propiedades"], models, [145*mm, 39*mm], PURPLE))
    story.append(Spacer(1, 4*mm))
    story.append(callout("Estos modelos no deben exponerse completos al LLM. Cada tool presenta un contrato reducido y construye el DTO completo en una capa de adaptación validada.", PURPLE_LIGHT, PURPLE))
    doc.build(story)
    return path


def build_architecture():
    path = OUT / "arquitectura-y-autenticacion.pdf"
    doc = NumberedDocTemplate(str(path), "Arquitectura y autenticación del agente", pagesize=A4,
                              leftMargin=18*mm, rightMargin=18*mm, topMargin=17*mm, bottomMargin=17*mm)
    story = cover("Arquitectura y\nautenticación", "Extracto técnico de la auditoría de la reunión del 13 de agosto", "Documento técnico 03", GOLD)

    story += section_title(3, "Arquitectura actual observada")
    story.append(p("El diagrama compartido representa la solución existente, no la arquitectura completa del agente."))
    story.append(captioned_drawing("Vista lógica observada de la plataforma actual", diagram_current_architecture()))
    current = [
        "SecurityAdmin FrontEnd y SecurityAdmin BackEnd administran identidad, roles y funcionalidades.",
        "AgroLink FrontEnd contiene módulos de caravanas, insumos y hacienda, además de integración AWS/Cloudflare.",
        "AgroLink BackEnd contiene caravanas, insumos, hacienda, fletes e integradores con PSIG y WinCampo.",
        "Existen varias APIs y componentes Docker en el mismo entorno.",
    ]
    for x in current: story.append(bullet(x))
    story.append(p("Vacíos del dibujo actual", "h2"))
    missing = ["API pública del agente", "orquestador", "base de conversaciones y memoria", "proveedor LLM", "almacenamiento de archivos", "monitoreo y auditoría", "límites de red pública, privada y VPN", "manejo de secretos", "flujo completo del JWT"]
    grid = [[missing[i], missing[i+1] if i+1 < len(missing) else ""] for i in range(0, len(missing), 2)]
    story.append(data_table(["Componente faltante", "Componente faltante"], grid, [92*mm, 92*mm], GOLD))
    story.append(Spacer(1, 4*mm))
    story.append(callout("El diagrama actual sirve como mapa del sistema anfitrión, pero no alcanza como diagrama de despliegue ni como modelo de seguridad del agente.", GOLD_LIGHT, GOLD))
    story.append(PageBreak())

    story += section_title(4, "Arquitectura objetivo recomendada")
    story.append(captioned_drawing("Componentes, fronteras y conectividad", diagram_target_architecture()))
    story.append(callout("La API Gateway es la frontera pública. El orquestador, la persistencia, los archivos y el backoffice permanecen dentro de la infraestructura controlada por el cliente.", TEAL_LIGHT, TEAL))

    layers = [
        ("4.1", "Componente Angular", [
            "Vive dentro del frontend de AgroLink.",
            "Obtiene el JWT desde el mecanismo actual de sesión, sin copiarlo a almacenamiento adicional.",
            "Envía mensajes y conversation_id a la API del agente.",
            "Renderiza un contrato estructurado de respuesta.",
            "No decide permisos ni consulta directamente tools internas.",
        ]),
        ("4.2", "API Gateway del agente", [
            "Valida cada petición contra SecurityAdmin o el mecanismo criptográfico oficial.",
            "Obtiene user_id, roles y claims desde el token validado.",
            "Ignora cualquier user_id enviado libremente por el navegador.",
            "Verifica que la conversación pertenezca al usuario.",
            "Aplica límites de tamaño, frecuencia y tiempo.",
            "Crea un request_id para trazabilidad.",
            "Pasa al orquestador solo los datos necesarios y normaliza errores.",
        ]),
        ("4.3", "Orquestador privado", [
            "n8n es una opción razonable, pero no fue definido en la reunión.",
            "Interpreta intención y selecciona tools permitidas.",
            "Combina resultados de una o varias operaciones de AgroLink.",
            "Genera texto, tablas, gráficos o archivos.",
            "Registra métricas sin guardar secretos y no queda abierto a Internet.",
        ]),
        ("4.4", "API de AgroLink", [
            "Es la fuente de verdad de los datos.",
            "Aplica la autorización real de cada operación.",
            "Recibe el JWT del usuario que originó la consulta.",
            "Responde 401 o 403 y no delega su modelo de permisos al agente.",
        ]),
        ("4.5", "Persistencia del agente", [
            "PostgreSQL es la recomendación inicial por concurrencia, trazabilidad, relaciones y backups.",
            "Almacena usuarios referenciados, conversaciones, mensajes, sesiones, resúmenes, preferencias, ejecuciones, archivos y auditoría.",
            "No almacena contraseñas, JWT completos, secretos del LLM ni credenciales dentro de workflows.",
        ]),
        ("4.6", "Backoffice y monitoreo", [
            "Separado de la API pública del chat.",
            "Acceso exclusivo por VPN o red administrativa.",
            "Permisos administrativos distintos de los usuarios de AgroLink.",
            "Datos minimizados, accesos trazados y política explícita de revisión.",
        ]),
    ]
    for idx, title, items in layers:
        story.append(p(f"{idx} {title}", "h2"))
        for x in items: story.append(bullet(x))
    story.append(PageBreak())

    story += section_title(5, "Flujo correcto de autenticación y autorización")
    story.append(captioned_drawing("Secuencia del JWT y aplicación de permisos", diagram_auth_sequence()))
    story.append(p("Respuesta concreta a la duda sobre la autenticación", "h2"))
    auth_steps = [
        "El usuario ya inició sesión en AgroLink.",
        "El frontend posee un JWT de esa sesión.",
        "El componente del chat envía ese JWT a la API del agente.",
        "La API del agente lo valida con SecurityAdmin.",
        "El agente usa ese mismo JWT al consultar AgroLink.",
        "AgroLink decide si la operación está permitida.",
    ]
    for i, x in enumerate(auth_steps, 1): story.append(p(f"<font name='DocSans-Bold' color='#087F8C'>{i}.</font> {x}"))
    story.append(Spacer(1, 4*mm))
    story.append(callout("El usuario y contraseña utilizados para ver Swagger protegen la documentación; no sustituyen el login ni el JWT operativo de la API.", RED_LIGHT, RED))
    story.append(Spacer(1, 4*mm))
    story.append(p("Según la reunión, el cliente todavía debía crear un usuario de prueba y dejar operativa una API accesible que emitiera o aceptara el JWT correspondiente."))
    story.append(p("Casos todavía pendientes", "h2"))
    pending = [
        "Endpoint exacto de login y formato de respuesta.",
        "Endpoint o método de validación del JWT.",
        "Issuer, audience, firma, expiración y clock skew.",
        "Renovación y revocación.",
        "Claims que identifican usuario, empresa y establecimientos.",
        "Qué ocurre si el token vence durante una ejecución larga.",
        "Credencial para trabajos automáticos sin usuario presente.",
        "Diferencia entre un usuario de AgroLink y un administrador de Solvo.",
    ]
    for x in pending: story.append(bullet(x))
    doc.build(story)
    return path


def main():
    outputs = [build_catalog(), build_model(), build_architecture()]
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
