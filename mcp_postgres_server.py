
"""
Servidor MCP para PostgreSQL
==============================
Expõe ferramentas para consulta ao banco via protocolo MCP.
Execute: python mcp_postgres_server.py
"""
import asyncio
import os
import json
import psycopg2
import psycopg2.extras
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configuração do banco (via variável de ambiente)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:senha@localhost:5432/meu_banco"
)

# Cria a instância do servidor MCP
server = Server("postgres-mcp-server")


def get_connection():
    """Retorna uma conexão com o banco PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


# ─── Define as ferramentas disponíveis ───────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Retorna a lista de ferramentas disponíveis neste servidor MCP."""
    return [
        types.Tool(
            name="executar_query",
            description="Executa uma query SELECT no banco PostgreSQL e retorna os resultados."
                        " APENAS queries SELECT são permitidas por segurança.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Query SQL SELECT para executar"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de linhas a retornar (default: 100)",
                        "default": 100
                    }
                },
                "required": ["sql"]
            }
        ),
        types.Tool(
            name="listar_tabelas",
            description="Lista todas as tabelas disponíveis no schema público do banco de dados.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="descrever_tabela",
            description="Retorna a estrutura de uma tabela: colunas, tipos de dados e constraints.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {
                        "type": "string",
                        "description": "Nome da tabela a ser descrita"
                    }
                },
                "required": ["tabela"]
            }
        ),
        types.Tool(
            name="contar_registros",
            description="Conta o número de registros em uma tabela, com filtro opcional.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {
                        "type": "string",
                        "description": "Nome da tabela"
                    },
                    "where": {
                        "type": "string",
                        "description": "Cláusula WHERE opcional (sem a palavra WHERE)"
                    }
                },
                "required": ["tabela"]
            }
        ),
    ]


# ─── Implementa a execução de cada ferramenta ─────────────────────────────────
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Executa a ferramenta solicitada com os argumentos fornecidos."""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if name == "executar_query":
            sql = arguments["sql"].strip()
            limite = arguments.get("limite", 100)

            # Segurança: apenas SELECT
            if not sql.upper().startswith("SELECT"):
                return [types.TextContent(
                    type="text",
                    text="⚠️ Apenas queries SELECT são permitidas por segurança."
                )]

            cur.execute(sql)
            rows = cur.fetchmany(limite)
            resultado = [dict(row) for row in rows]
            return [types.TextContent(
                type="text",
                text=json.dumps(resultado, ensure_ascii=False, default=str, indent=2)
            )]

        elif name == "listar_tabelas":
            cur.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name) as num_colunas
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tabelas = [dict(row) for row in cur.fetchall()]
            return [types.TextContent(
                type="text",
                text=json.dumps(tabelas, ensure_ascii=False, indent=2)
            )]

        elif name == "descrever_tabela":
            tabela = arguments["tabela"]
            cur.execute("""
                SELECT 
                    column_name as coluna,
                    data_type as tipo,
                    character_maximum_length as tamanho_max,
                    is_nullable as permite_nulo,
                    column_default as valor_padrao
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (tabela,))
            colunas = [dict(row) for row in cur.fetchall()]
            if not colunas:
                return [types.TextContent(type="text", text=f"Tabela '{tabela}' não encontrada.")]
            return [types.TextContent(
                type="text",
                text=json.dumps({"tabela": tabela, "colunas": colunas}, 
                               ensure_ascii=False, default=str, indent=2)
            )]

        elif name == "contar_registros":
            tabela = arguments["tabela"]
            where = arguments.get("where", "")
            sql = f"SELECT COUNT(*) as total FROM {tabela}"
            if where:
                sql += f" WHERE {where}"
            cur.execute(sql)
            total = cur.fetchone()["total"]
            return [types.TextContent(
                type="text",
                text=f"Total de registros em '{tabela}'{' (com filtro)' if where else '': {total}"
            )]

        conn.close()

    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Erro: {str(e)}")]


# ─── Ponto de entrada do servidor ─────────────────────────────────────────────
async def main():
    print(f"🚀 Servidor MCP PostgreSQL iniciado", flush=True)
    print(f"   Banco: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}", flush=True)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
