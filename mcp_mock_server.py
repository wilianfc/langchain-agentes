
"""
Servidor MCP Mock (para testes sem PostgreSQL)
Simula um banco de dados com dados de exemplo.
"""
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

server = Server("postgres-mock-server")

# Dados simulados
MOCK_DATA = {
    "clientes": [
        {"id": 1, "nome": "Ana Silva", "email": "ana@exemplo.com", "cidade": "São Paulo", "saldo": 15000.00},
        {"id": 2, "nome": "Bruno Costa", "email": "bruno@exemplo.com", "cidade": "Rio de Janeiro", "saldo": 8500.50},
        {"id": 3, "nome": "Carla Mendes", "email": "carla@exemplo.com", "cidade": "Curitiba", "saldo": 22000.00},
        {"id": 4, "nome": "Diego Santos", "email": "diego@exemplo.com", "cidade": "São Paulo", "saldo": 5200.75},
    ],
    "produtos": [
        {"id": 1, "nome": "Notebook Pro", "categoria": "Eletrônicos", "preco": 4500.00, "estoque": 15},
        {"id": 2, "nome": "Smartphone X", "categoria": "Eletrônicos", "preco": 2800.00, "estoque": 42},
        {"id": 3, "nome": "Mesa Gamer", "categoria": "Móveis", "preco": 1200.00, "estoque": 8},
        {"id": 4, "nome": "Cadeira Ergonômica", "categoria": "Móveis", "preco": 950.00, "estoque": 20},
    ],
    "pedidos": [
        {"id": 1, "cliente_id": 1, "produto_id": 2, "quantidade": 1, "total": 2800.00, "status": "entregue"},
        {"id": 2, "cliente_id": 2, "produto_id": 1, "quantidade": 1, "total": 4500.00, "status": "processando"},
        {"id": 3, "cliente_id": 1, "produto_id": 4, "quantidade": 2, "total": 1900.00, "status": "entregue"},
        {"id": 4, "cliente_id": 3, "produto_id": 3, "quantidade": 1, "total": 1200.00, "status": "enviado"},
    ]
}

SCHEMAS = {
    "clientes": [
        {"coluna": "id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "nome", "tipo": "varchar", "permite_nulo": "NO"},
        {"coluna": "email", "tipo": "varchar", "permite_nulo": "NO"},
        {"coluna": "cidade", "tipo": "varchar", "permite_nulo": "YES"},
        {"coluna": "saldo", "tipo": "numeric", "permite_nulo": "YES"},
    ],
    "produtos": [
        {"coluna": "id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "nome", "tipo": "varchar", "permite_nulo": "NO"},
        {"coluna": "categoria", "tipo": "varchar", "permite_nulo": "YES"},
        {"coluna": "preco", "tipo": "numeric", "permite_nulo": "NO"},
        {"coluna": "estoque", "tipo": "integer", "permite_nulo": "YES"},
    ],
    "pedidos": [
        {"coluna": "id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "cliente_id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "produto_id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "quantidade", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "total", "tipo": "numeric", "permite_nulo": "NO"},
        {"coluna": "status", "tipo": "varchar", "permite_nulo": "YES"},
    ]
}

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="executar_query",
            description="Executa uma query no banco mock (suporta filtros simples por coluna=valor)",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {"type": "string", "description": "Nome da tabela"},
                    "filtro": {"type": "object", "description": "Filtros chave:valor (opcional)"}
                },
                "required": ["tabela"]
            }
        ),
        types.Tool(
            name="listar_tabelas",
            description="Lista todas as tabelas disponíveis no banco mock.",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="descrever_tabela",
            description="Retorna o schema de uma tabela.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {"type": "string", "description": "Nome da tabela"}
                },
                "required": ["tabela"]
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "listar_tabelas":
        tabelas = [{"table_name": t, "num_colunas": len(c)} for t, c in SCHEMAS.items()]
        return [types.TextContent(type="text", text=json.dumps(tabelas, ensure_ascii=False, indent=2))]

    elif name == "descrever_tabela":
        tabela = arguments["tabela"]
        schema = SCHEMAS.get(tabela)
        if not schema:
            return [types.TextContent(type="text", text=f"Tabela '{tabela}' não encontrada. Tabelas: {list(SCHEMAS.keys())}")]
        return [types.TextContent(
            type="text",
            text=json.dumps({"tabela": tabela, "colunas": schema}, ensure_ascii=False, indent=2)
        )]

    elif name == "executar_query":
        tabela = arguments["tabela"]
        filtro = arguments.get("filtro", {})
        dados = MOCK_DATA.get(tabela, [])
        if filtro:
            dados = [row for row in dados 
                    if all(str(row.get(k)) == str(v) for k, v in filtro.items())]
        return [types.TextContent(
            type="text",
            text=json.dumps(dados, ensure_ascii=False, default=str, indent=2)
        )]

    return [types.TextContent(type="text", text=f"Ferramenta desconhecida: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
