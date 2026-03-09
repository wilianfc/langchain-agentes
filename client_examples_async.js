/**
 * Cliente JavaScript/TypeScript para API Assíncrona LangChain
 * ============================================================
 * 
 * Exemplos de como consumir a API assíncrona em aplicações frontend
 * (React, Angular, Vue, etc.) ou Node.js backend.
 */

// ============================================================================
// EXEMPLO 1: Cliente Básico (Vanilla JavaScript)
// ============================================================================

class LangChainAsyncClient {
    constructor(apiUrl, maxWaitTime = 300000) {
        this.apiUrl = apiUrl.replace(/\/$/, ''); // Remove trailing slash
        this.maxWaitTime = maxWaitTime; // 5 minutos em ms
    }

    /**
     * Envia consulta e retorna Promise com resultado
     */
    async query(clienteId, dadosCliente, pergunta, modo = 'segmento') {
        try {
            // 1. Enviar requisição
            const requestId = await this._sendRequest(
                clienteId, 
                dadosCliente, 
                pergunta, 
                modo
            );
            
            if (!requestId) {
                throw new Error('Falha ao enviar requisição');
            }

            // 2. Aguardar resultado com polling
            return await this._pollWithBackoff(requestId);

        } catch (error) {
            console.error('❌ Erro na consulta:', error);
            throw error;
        }
    }

    async _sendRequest(clienteId, dadosCliente, pergunta, modo) {
        const response = await fetch(`${this.apiUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cliente_id: clienteId,
                dados_cliente: dadosCliente,
                pergunta: pergunta,
                modo: modo
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`✅ Requisição enviada: ${data.request_id}`);
        return data.request_id;
    }

    async _pollWithBackoff(requestId) {
        const startTime = Date.now();
        let waitTime = 1000; // Começar com 1 segundo
        const maxWait = 10000; // Máximo 10 segundos

        while (true) {
            // Verificar timeout
            const elapsed = Date.now() - startTime;
            if (elapsed > this.maxWaitTime) {
                throw new Error(`Timeout após ${elapsed / 1000}s`);
            }

            // Consultar status
            const response = await fetch(`${this.apiUrl}/status/${requestId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const status = data.status;

            if (status === 'COMPLETED') {
                console.log(`✅ Concluído em ${elapsed / 1000}s`);
                return data.result;
            }

            if (status === 'FAILED') {
                throw new Error(data.error || 'Processamento falhou');
            }

            // Aguardar antes da próxima consulta
            console.log(`⏳ Status: ${status} (aguardando ${waitTime / 1000}s)`);
            await this._sleep(waitTime);

            // Exponential backoff
            waitTime = Math.min(waitTime * 2, maxWait);
        }
    }

    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}


// ============================================================================
// EXEMPLO 2: React Component com UI
// ============================================================================

/**
 * Hook React para usar a API assíncrona
 */
function useLangChainQuery() {
    const [loading, setLoading] = React.useState(false);
    const [progress, setProgress] = React.useState(null);
    const [result, setResult] = React.useState(null);
    const [error, setError] = React.useState(null);

    const query = async (clienteId, dadosCliente, pergunta, modo = 'segmento') => {
        setLoading(true);
        setProgress('Enviando requisição...');
        setResult(null);
        setError(null);

        const apiUrl = process.env.REACT_APP_API_URL;
        const client = new LangChainAsyncClient(apiUrl);

        try {
            // Enviar requisição
            const response = await fetch(`${apiUrl}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cliente_id: clienteId,
                    dados_cliente: dadosCliente,
                    pergunta: pergunta,
                    modo: modo
                })
            });

            const { request_id } = await response.json();
            setProgress(`Processando... (ID: ${request_id})`);

            // Polling com atualizações de progresso
            let waitTime = 1000;
            const maxWait = 10000;
            const startTime = Date.now();

            while (true) {
                const statusResponse = await fetch(`${apiUrl}/status/${request_id}`);
                const statusData = await statusResponse.json();

                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                setProgress(`${statusData.status}... (${elapsed}s)`);

                if (statusData.status === 'COMPLETED') {
                    setResult(statusData.result);
                    setLoading(false);
                    break;
                }

                if (statusData.status === 'FAILED') {
                    throw new Error(statusData.error || 'Processamento falhou');
                }

                await new Promise(resolve => setTimeout(resolve, waitTime));
                waitTime = Math.min(waitTime * 2, maxWait);
            }

        } catch (err) {
            setError(err.message);
            setLoading(false);
        }
    };

    return { loading, progress, result, error, query };
}

/**
 * Componente React de exemplo
 */
function ChatComponent() {
    const { loading, progress, result, error, query } = useLangChainQuery();
    const [pergunta, setPergunta] = React.useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        await query(
            'C12345',
            {
                idade: 35,
                renda_mensal: 5000,
                saldo_medio: 8000,
                transacoes_mes: 15,
                score_credito: 680,
                num_produtos: 3
            },
            pergunta,
            'segmento'
        );
    };

    return (
        <div className="chat-container">
            <form onSubmit={handleSubmit}>
                <textarea
                    value={pergunta}
                    onChange={(e) => setPergunta(e.target.value)}
                    placeholder="Digite sua pergunta..."
                    disabled={loading}
                />
                <button type="submit" disabled={loading}>
                    {loading ? 'Processando...' : 'Enviar'}
                </button>
            </form>

            {loading && (
                <div className="loading">
                    <div className="spinner"></div>
                    <p>{progress}</p>
                </div>
            )}

            {error && (
                <div className="error">
                    ❌ Erro: {error}
                </div>
            )}

            {result && (
                <div className="result">
                    <h3>Resultado:</h3>
                    <p><strong>Segmento:</strong> {result.segmento}</p>
                    <p><strong>Resposta:</strong> {result.resposta}</p>
                </div>
            )}
        </div>
    );
}


// ============================================================================
// EXEMPLO 3: Angular Service
// ============================================================================

/**
 * Service Angular para consumir API assíncrona
 */
/*
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, throwError } from 'rxjs';
import { switchMap, takeWhile, catchError, map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class LangChainService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  query(
    clienteId: string,
    dadosCliente: any,
    pergunta: string,
    modo: string = 'segmento'
  ): Observable<any> {
    // 1. Enviar requisição
    return this.http.post<{ request_id: string }>(`${this.apiUrl}/query`, {
      cliente_id: clienteId,
      dados_cliente: dadosCliente,
      pergunta: pergunta,
      modo: modo
    }).pipe(
      // 2. Iniciar polling
      switchMap(({ request_id }) => this.pollStatus(request_id))
    );
  }

  private pollStatus(requestId: string): Observable<any> {
    return interval(2000).pipe( // Consultar a cada 2 segundos
      switchMap(() => this.http.get<any>(`${this.apiUrl}/status/${requestId}`)),
      takeWhile(response => {
        // Continuar enquanto estiver PENDING ou PROCESSING
        return response.status !== 'COMPLETED' && response.status !== 'FAILED';
      }, true), // Incluir o último valor
      map(response => {
        if (response.status === 'COMPLETED') {
          return response.result;
        }
        if (response.status === 'FAILED') {
          throw new Error(response.error || 'Processamento falhou');
        }
        return response; // Retornar status intermediário
      }),
      catchError(error => {
        console.error('Erro no polling:', error);
        return throwError(() => error);
      })
    );
  }
}
*/


// ============================================================================
// EXEMPLO 4: Node.js Backend (Express)
// ============================================================================

/**
 * Rota Express que usa a API assíncrona como proxy
 */
/*
const express = require('express');
const axios = require('axios');

const router = express.Router();
const LANGCHAIN_API_URL = process.env.LANGCHAIN_API_URL;

router.post('/consulta', async (req, res) => {
    const { cliente_id, dados_cliente, pergunta, modo } = req.body;

    try {
        // 1. Enviar para API assíncrona
        const { data: { request_id } } = await axios.post(
            `${LANGCHAIN_API_URL}/query`,
            { cliente_id, dados_cliente, pergunta, modo }
        );

        // 2. Retornar request_id imediatamente
        res.status(202).json({
            request_id,
            status: 'PENDING',
            message: `Consulte GET /consulta/${request_id} para ver o resultado`
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.get('/consulta/:request_id', async (req, res) => {
    const { request_id } = req.params;

    try {
        const { data } = await axios.get(
            `${LANGCHAIN_API_URL}/status/${request_id}`
        );

        res.json(data);

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
*/


// ============================================================================
// EXEMPLO 5: TypeScript com Tipos
// ============================================================================

interface DadosCliente {
    idade: number;
    renda_mensal: number;
    saldo_medio: number;
    transacoes_mes: number;
    score_credito: number;
    num_produtos: number;
}

interface QueryRequest {
    cliente_id: string;
    dados_cliente: DadosCliente;
    pergunta: string;
    modo: 'segmento' | 'persona' | 'rag';
}

interface QueryResponse {
    request_id: string;
    status: 'PENDING';
    message: string;
}

interface StatusResponse {
    request_id: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    result?: any;
    error?: string;
    created_at?: string;
    started_at?: string;
    completed_at?: string;
}

class TypedLangChainClient {
    constructor(
        private apiUrl: string,
        private maxWaitTime: number = 300000
    ) {
        this.apiUrl = apiUrl.replace(/\/$/, '');
    }

    async query(request: QueryRequest): Promise<any> {
        // 1. Enviar requisição
        const response = await fetch(`${this.apiUrl}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const { request_id }: QueryResponse = await response.json();

        // 2. Polling
        return this.pollStatus(request_id);
    }

    private async pollStatus(requestId: string): Promise<any> {
        const startTime = Date.now();
        let waitTime = 1000;
        const maxWait = 10000;

        while (true) {
            if (Date.now() - startTime > this.maxWaitTime) {
                throw new Error('Timeout');
            }

            const response = await fetch(`${this.apiUrl}/status/${requestId}`);
            const data: StatusResponse = await response.json();

            if (data.status === 'COMPLETED') {
                return data.result;
            }

            if (data.status === 'FAILED') {
                throw new Error(data.error || 'Failed');
            }

            await this.sleep(waitTime);
            waitTime = Math.min(waitTime * 2, maxWait);
        }
    }

    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}


// ============================================================================
// EXEMPLO DE USO
// ============================================================================

// Vanilla JS
const client = new LangChainAsyncClient('https://seu-endpoint.execute-api.us-east-1.amazonaws.com');

client.query(
    'C12345',
    {
        idade: 35,
        renda_mensal: 5000,
        saldo_medio: 8000,
        transacoes_mes: 15,
        score_credito: 680,
        num_produtos: 3
    },
    'Quais produtos você recomenda?',
    'segmento'
)
.then(result => {
    console.log('✅ Resultado:', result);
})
.catch(error => {
    console.error('❌ Erro:', error);
});

// TypeScript
const typedClient = new TypedLangChainClient('https://seu-endpoint...');

(async () => {
    try {
        const result = await typedClient.query({
            cliente_id: 'C12345',
            dados_cliente: {
                idade: 35,
                renda_mensal: 5000,
                saldo_medio: 8000,
                transacoes_mes: 15,
                score_credito: 680,
                num_produtos: 3
            },
            pergunta: 'Quais produtos você recomenda?',
            modo: 'segmento'
        });

        console.log('✅ Resultado:', result);
    } catch (error) {
        console.error('❌ Erro:', error);
    }
})();

// Export para uso em módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        LangChainAsyncClient,
        TypedLangChainClient
    };
}
