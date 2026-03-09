"""
Helper para renderizar diagramas Mermaid em Jupyter notebooks.

Uso:
    from mermaid_helper import mermaid
    
    mermaid('''
    graph TD
        A[Start] --> B[End]
    ''')
"""

from IPython.display import HTML, display
import uuid

def mermaid(diagram: str, height: int = 400) -> None:
    """
    Renderiza um diagrama Mermaid no Jupyter notebook.
    
    Args:
        diagram: String com o código Mermaid
        height: Altura do diagrama em pixels (default: 400)
    """
    diagram_id = f"mermaid_{uuid.uuid4().hex[:8]}"
    
    html = f"""
    <div id="{diagram_id}" style="max-width: 100%; overflow-x: auto;"></div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            themeVariables: {{
                fontSize: '16px'
            }}
        }});
        
        const diagram = `{diagram.strip()}`;
        const element = document.getElementById('{diagram_id}');
        
        try {{
            const {{ svg }} = await mermaid.render('mermaid_svg_{diagram_id}', diagram);
            element.innerHTML = svg;
        }} catch (error) {{
            element.innerHTML = `<div style="color: red; padding: 10px; border: 1px solid red;">
                <b>Erro ao renderizar Mermaid:</b><br>${{error.message}}
            </div>`;
            console.error('Mermaid error:', error);
        }}
    </script>
    """
    
    display(HTML(html))


def show_mermaid_examples():
    """Exibe exemplos de diagramas Mermaid."""
    
    print("📊 Exemplo 1: Fluxograma")
    mermaid('''
    graph TD
        A[Início] --> B{Decisão}
        B -->|Sim| C[Ação 1]
        B -->|Não| D[Ação 2]
        C --> E[Fim]
        D --> E
        style A fill:#4CAF50,color:#fff
        style E fill:#F44336,color:#fff
    ''')
    
    print("\n📊 Exemplo 2: Diagrama de Sequência")
    mermaid('''
    sequenceDiagram
        participant U as Usuário
        participant A as Agente
        participant T as Tool
        U->>A: Pergunta
        A->>T: Chama Tool
        T->>A: Resultado
        A->>U: Resposta
    ''')
    
    print("\n📊 Exemplo 3: Diagrama de Estados")
    mermaid('''
    stateDiagram-v2
        [*] --> PENDING
        PENDING --> PROCESSING
        PROCESSING --> COMPLETED
        PROCESSING --> FAILED
        COMPLETED --> [*]
        FAILED --> [*]
    ''')
