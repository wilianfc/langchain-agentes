"""
Exemplos de Cliente para API Assíncrona LangChain
===================================================

Este arquivo contém exemplos práticos de como consumir a nova API assíncrona
que resolve o problema de timeout de 30 segundos.
"""

import requests
import time
from typing import Dict, Optional
import json


# ============================================================================
# EXEMPLO 1: Cliente Básico com Polling Simples
# ============================================================================

def exemplo_basico():
    """Exemplo mais simples de uso da API assíncrona"""
    
    # URL da API (obter do Terraform output)
    API_URL = "https://seu-endpoint.execute-api.us-east-1.amazonaws.com"
    
    # 1. Enviar requisição assíncrona
    response = requests.post(
        f"{API_URL}/query",
        json={
            "cliente_id": "C12345",
            "dados_cliente": {
                "idade": 35,
                "renda_mensal": 5000,
                "saldo_medio": 8000,
                "transacoes_mes": 15,
                "score_credito": 680,
                "num_produtos": 3
            },
            "pergunta": "Quais produtos você recomenda?",
            "modo": "segmento"
        }
    )
    
    data = response.json()
    request_id = data["request_id"]
    print(f"✅ Requisição enviada: {request_id}")
    
    # 2. Fazer polling até completar
    while True:
        status_response = requests.get(f"{API_URL}/status/{request_id}")
        status_data = status_response.json()
        
        status = status_data["status"]
        print(f"⏳ Status: {status}")
        
        if status == "COMPLETED":
            print(f"✅ Resultado: {status_data['result']}")
            break
        elif status == "FAILED":
            print(f"❌ Erro: {status_data.get('error')}")
            break
        
        # Aguardar antes de consultar novamente
        time.sleep(5)


# ============================================================================
# EXEMPLO 2: Cliente com Exponential Backoff
# ============================================================================

class AsyncLangChainClient:
    """Cliente robusto com retry e exponential backoff"""
    
    def __init__(self, api_url: str, max_wait_time: int = 300):
        """
        Args:
            api_url: URL base da API
            max_wait_time: Tempo máximo de espera em segundos (padrão: 5 min)
        """
        self.api_url = api_url.rstrip("/")
        self.max_wait_time = max_wait_time
    
    def query(self, 
              cliente_id: str,
              dados_cliente: Dict,
              pergunta: str,
              modo: str = "segmento") -> Optional[Dict]:
        """
        Envia consulta e aguarda resultado com exponential backoff
        
        Returns:
            Resultado da consulta ou None se falhar
        """
        # 1. Enviar requisição
        request_id = self._send_request(cliente_id, dados_cliente, pergunta, modo)
        if not request_id:
            return None
        
        # 2. Aguardar com exponential backoff
        return self._poll_with_backoff(request_id)
    
    def _send_request(self, 
                      cliente_id: str,
                      dados_cliente: Dict,
                      pergunta: str,
                      modo: str) -> Optional[str]:
        """Envia requisição e retorna request_id"""
        try:
            response = requests.post(
                f"{self.api_url}/query",
                json={
                    "cliente_id": cliente_id,
                    "dados_cliente": dados_cliente,
                    "pergunta": pergunta,
                    "modo": modo
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            request_id = data["request_id"]
            print(f"✅ Requisição enviada: {request_id}")
            return request_id
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao enviar requisição: {e}")
            return None
    
    def _poll_with_backoff(self, request_id: str) -> Optional[Dict]:
        """
        Faz polling com exponential backoff
        
        Intervalo de consultas:
        - 1s, 2s, 4s, 8s, 10s, 10s, 10s...
        """
        start_time = time.time()
        wait_time = 1  # Começar com 1 segundo
        max_wait = 10  # Máximo de 10 segundos entre consultas
        
        while True:
            # Verificar timeout
            elapsed = time.time() - start_time
            if elapsed > self.max_wait_time:
                print(f"⏱️ Timeout após {elapsed:.1f}s")
                return None
            
            # Consultar status
            try:
                response = requests.get(
                    f"{self.api_url}/status/{request_id}",
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()
                
                status = data["status"]
                
                if status == "COMPLETED":
                    print(f"✅ Concluído em {elapsed:.1f}s")
                    return data["result"]
                
                elif status == "FAILED":
                    error = data.get("error", "Erro desconhecido")
                    print(f"❌ Falha: {error}")
                    return None
                
                else:
                    print(f"⏳ Status: {status} (aguardando {wait_time}s)")
                    time.sleep(wait_time)
                    
                    # Exponential backoff
                    wait_time = min(wait_time * 2, max_wait)
                    
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Erro ao consultar status: {e}")
                time.sleep(wait_time)


# ============================================================================
# EXEMPLO 3: Cliente Assíncrono (asyncio)
# ============================================================================

import asyncio
import aiohttp

class AsyncioLangChainClient:
    """Cliente totalmente assíncrono usando asyncio"""
    
    def __init__(self, api_url: str, max_wait_time: int = 300):
        self.api_url = api_url.rstrip("/")
        self.max_wait_time = max_wait_time
    
    async def query(self,
                    cliente_id: str,
                    dados_cliente: Dict,
                    pergunta: str,
                    modo: str = "segmento") -> Optional[Dict]:
        """Versão async do método query"""
        
        async with aiohttp.ClientSession() as session:
            # 1. Enviar requisição
            request_id = await self._send_request(
                session, cliente_id, dados_cliente, pergunta, modo
            )
            if not request_id:
                return None
            
            # 2. Aguardar com backoff
            return await self._poll_with_backoff(session, request_id)
    
    async def _send_request(self,
                           session: aiohttp.ClientSession,
                           cliente_id: str,
                           dados_cliente: Dict,
                           pergunta: str,
                           modo: str) -> Optional[str]:
        """Envia requisição (async)"""
        try:
            async with session.post(
                f"{self.api_url}/query",
                json={
                    "cliente_id": cliente_id,
                    "dados_cliente": dados_cliente,
                    "pergunta": pergunta,
                    "modo": modo
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                request_id = data["request_id"]
                print(f"✅ Requisição enviada: {request_id}")
                return request_id
                
        except Exception as e:
            print(f"❌ Erro ao enviar requisição: {e}")
            return None
    
    async def _poll_with_backoff(self,
                                 session: aiohttp.ClientSession,
                                 request_id: str) -> Optional[Dict]:
        """Polling com backoff (async)"""
        start_time = time.time()
        wait_time = 1
        max_wait = 10
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.max_wait_time:
                print(f"⏱️ Timeout após {elapsed:.1f}s")
                return None
            
            try:
                async with session.get(
                    f"{self.api_url}/status/{request_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    status = data["status"]
                    
                    if status == "COMPLETED":
                        print(f"✅ Concluído em {elapsed:.1f}s")
                        return data["result"]
                    
                    elif status == "FAILED":
                        error = data.get("error", "Erro desconhecido")
                        print(f"❌ Falha: {error}")
                        return None
                    
                    else:
                        print(f"⏳ Status: {status}")
                        await asyncio.sleep(wait_time)
                        wait_time = min(wait_time * 2, max_wait)
                        
            except Exception as e:
                print(f"⚠️ Erro ao consultar status: {e}")
                await asyncio.sleep(wait_time)


# ============================================================================
# EXEMPLO 4: Múltiplas Requisições em Paralelo
# ============================================================================

async def processar_em_lote(clientes: list):
    """
    Processa múltiplos clientes em paralelo
    
    Args:
        clientes: Lista de dicts com dados dos clientes
    """
    API_URL = "https://seu-endpoint.execute-api.us-east-1.amazonaws.com"
    client = AsyncioLangChainClient(API_URL)
    
    # Criar tarefas para todos os clientes
    tasks = []
    for cliente in clientes:
        task = client.query(
            cliente_id=cliente["id"],
            dados_cliente=cliente["dados"],
            pergunta=cliente["pergunta"],
            modo=cliente.get("modo", "segmento")
        )
        tasks.append(task)
    
    # Executar todas em paralelo
    results = await asyncio.gather(*tasks)
    
    # Processar resultados
    for cliente, result in zip(clientes, results):
        if result:
            print(f"Cliente {cliente['id']}: ✅ {result['segmento']}")
        else:
            print(f"Cliente {cliente['id']}: ❌ Falhou")
    
    return results


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Configurar API URL (obter do Terraform)
    API_URL = "https://seu-endpoint.execute-api.us-east-1.amazonaws.com"
    
    # Exemplo 1: Cliente básico
    print("\n=== EXEMPLO 1: Cliente Básico ===")
    # exemplo_basico()
    
    # Exemplo 2: Cliente com retry
    print("\n=== EXEMPLO 2: Cliente com Exponential Backoff ===")
    client = AsyncLangChainClient(API_URL, max_wait_time=300)
    resultado = client.query(
        cliente_id="C12345",
        dados_cliente={
            "idade": 35,
            "renda_mensal": 5000,
            "saldo_medio": 8000,
            "transacoes_mes": 15,
            "score_credito": 680,
            "num_produtos": 3
        },
        pergunta="Quais produtos você recomenda?",
        modo="segmento"
    )
    
    if resultado:
        print(f"\n📊 Resultado Final:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    # Exemplo 3: Cliente asyncio
    print("\n=== EXEMPLO 3: Cliente Async ===")
    async_client = AsyncioLangChainClient(API_URL)
    # resultado_async = asyncio.run(async_client.query(...))
    
    # Exemplo 4: Processamento em lote
    print("\n=== EXEMPLO 4: Processamento em Lote ===")
    clientes = [
        {
            "id": "C001",
            "dados": {"idade": 25, "renda_mensal": 3000, "saldo_medio": 2000},
            "pergunta": "Quais produtos para mim?",
            "modo": "segmento"
        },
        {
            "id": "C002",
            "dados": {"idade": 45, "renda_mensal": 10000, "saldo_medio": 50000},
            "pergunta": "Investimentos recomendados?",
            "modo": "persona"
        },
        # ... mais clientes
    ]
    # resultados_lote = asyncio.run(processar_em_lote(clientes))
