"""
Converte blocos ```plantuml ... ``` em células markdown do notebook
para URLs de imagem Kroki renderizáveis: ![Diagrama](https://kroki.io/plantuml/svg/...)
"""
import json
import re
import zlib
import base64
from pathlib import Path


def kroki_encode(text: str) -> str:
    compressed = zlib.compress(text.encode("utf-8"))[2:-4]
    b64 = base64.urlsafe_b64encode(compressed).decode("ascii")
    return b64.rstrip("=")


def plantuml_block_to_kroki(match: re.Match) -> str:
    plantuml_code = match.group(1).strip()
    encoded = kroki_encode(plantuml_code)
    url = f"https://kroki.io/plantuml/svg/{encoded}"
    return f'![Diagrama PlantUML]({url})'


def convert_notebook(notebook_path: Path) -> None:
    with open(notebook_path, encoding="utf-8") as f:
        nb = json.load(f)

    pattern = re.compile(r"```plantuml\n(.*?)```", re.DOTALL)
    changed = 0

    for cell in nb["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        source = "".join(cell["source"])
        new_source, n = pattern.subn(plantuml_block_to_kroki, source)
        if n:
            cell["source"] = [new_source]
            changed += n
            print(f"  Convertido {n} diagrama(s) em célula markdown")

    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"\nTotal: {changed} diagrama(s) convertido(s) para URLs Kroki em '{notebook_path}'")


if __name__ == "__main__":
    notebook = Path(__file__).parent / "langchain.ipynb"
    print(f"Convertendo: {notebook}\n")
    convert_notebook(notebook)
    print("Pronto! Reabra o notebook no VS Code para ver os diagramas renderizados.")
