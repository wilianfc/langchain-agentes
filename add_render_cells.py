import json, re, zlib, base64, string

def kroki_decode(encoded):
    padded = encoded + "=" * (-len(encoded) % 4)
    compressed = base64.urlsafe_b64decode(padded)
    return zlib.decompress(compressed, -15).decode("utf-8")

def make_python_cell(plantuml_code):
    escaped = plantuml_code.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    src = (
        "from plantuml_helper import show_plantuml\n\n"
        'show_plantuml("""\n'
        + plantuml_code.strip() + "\n"
        + '""")'
    )
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": "",
        "metadata": {},
        "outputs": [],
        "source": [src]
    }

with open("langchain.ipynb", encoding="utf-8") as f:
    nb = json.load(f)

pattern = re.compile(r"!\[Diagrama PlantUML\]\(https://kroki\.io/plantuml/svg/([^)]+)\)")

new_cells = []
changed = 0

for cell in nb["cells"]:
    new_cells.append(cell)
    if cell["cell_type"] != "markdown":
        continue
    source = "".join(cell["source"])
    m = pattern.search(source)
    if not m:
        continue
    plantuml_code = kroki_decode(m.group(1))
    # Remove a imagem do markdown (o Python cell vai renderizar)
    new_source = pattern.sub("", source).strip()
    cell["source"] = [new_source]
    # Adiciona Python cell depois
    new_cells.append(make_python_cell(plantuml_code))
    changed += 1
    print("  + celula Python adicionada apos cell markdown de diagrama")

nb["cells"] = new_cells

with open("langchain.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\nTotal: {changed} celulas Python inseridas no notebook")