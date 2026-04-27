import zlib
import urllib.request
from IPython.display import HTML, display


def _encode_plantuml(text):
    """Codifica PlantUML para o formato do servidor plantuml.com."""
    raw = zlib.compress(text.encode("utf-8"))[2:-4]  # raw DEFLATE sem header zlib

    def encode6bit(b):
        b = b & 0x3F
        if b < 10: return chr(ord("0") + b)
        b -= 10
        if b < 26: return chr(ord("A") + b)
        b -= 26
        if b < 26: return chr(ord("a") + b)
        b -= 26
        return "-" if b == 0 else "_"

    def encode3bytes(b1, b2, b3):
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        return encode6bit(c1) + encode6bit(c2) + encode6bit(c3) + encode6bit(c4)

    result = ""
    i = 0
    while i < len(raw):
        b1 = raw[i] if i < len(raw) else 0
        b2 = raw[i + 1] if i + 1 < len(raw) else 0
        b3 = raw[i + 2] if i + 2 < len(raw) else 0
        result += encode3bytes(b1, b2, b3)
        i += 3
    return result


def show_plantuml(diagram, title=""):
    """Renderiza PlantUML inline no notebook via plantuml.com."""
    encoded = _encode_plantuml(diagram.strip())
    url = "https://www.plantuml.com/plantuml/svg/" + encoded

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "image/svg+xml"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            svg = resp.read().decode("utf-8")

        title_html = (
            '<p style="text-align:center;font-style:italic;color:#555;margin:4px 0">'
            + title + "</p>"
        ) if title else ""
        html = (
            '<div style="text-align:center;margin:12px 0;padding:8px;'
            'background:#fafafa;border:1px solid #e0e0e0;border-radius:6px;">'
            + svg + title_html + "</div>"
        )
        display(HTML(html))

    except Exception as e:
        fallback = '<a href="' + url + '" target="_blank">Ver no PlantUML Server</a>'
        display(HTML(
            '<div style="color:#c62828;padding:8px;border:1px solid #c62828;border-radius:4px;">'
            "<b>Erro ao renderizar:</b> " + str(e) + "<br/>" + fallback + "</div>"
        ))


plantuml = show_plantuml