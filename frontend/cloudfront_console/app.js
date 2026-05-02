(() => {
  const config = window.APP_CONFIG || {};
  const apiUrl = (config.apiUrl || '').replace(/\/$/, '');

  const endpointEl = document.getElementById('api-endpoint');
  const queryForm = document.getElementById('query-form');
  const uploadForm = document.getElementById('upload-form');
  const queryStatus = document.getElementById('query-status');
  const queryResult = document.getElementById('query-result');
  const uploadResult = document.getElementById('upload-result');
  const queryBadge = document.getElementById('query-badge');
  const uploadBadge = document.getElementById('upload-badge');
  const fileInput = document.getElementById('arquivo_documento');
  const textArea = document.getElementById('texto_documento');

  endpointEl.textContent = apiUrl || 'API não configurada. Ajuste window.APP_CONFIG.apiUrl no deploy.';

  function setBadge(el, state, text) {
    el.className = `status-badge ${state}`;
    el.textContent = text;
  }

  function maybeNumber(value) {
    return value === '' || value === null || value === undefined ? undefined : Number(value);
  }

  function buildDadosCliente() {
    const data = {
      idade: maybeNumber(document.getElementById('idade').value),
      renda_mensal: maybeNumber(document.getElementById('renda_mensal').value),
      saldo_medio: maybeNumber(document.getElementById('saldo_medio').value),
      transacoes_mes: maybeNumber(document.getElementById('transacoes_mes').value),
      score_credito: maybeNumber(document.getElementById('score_credito').value),
      num_produtos: maybeNumber(document.getElementById('num_produtos').value),
      canal_digital: document.getElementById('canal_digital').checked,
      inadimplente: document.getElementById('inadimplente').checked,
    };

    const filled = Object.fromEntries(Object.entries(data).filter(([, value]) => value !== undefined));
    return Object.keys(filled).length ? filled : undefined;
  }

  async function requestJson(path, payload, method = 'POST') {
    if (!apiUrl) {
      throw new Error('API URL não configurada no frontend.');
    }

    const response = await fetch(`${apiUrl}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: payload ? JSON.stringify(payload) : undefined,
    });

    const text = await response.text();
    const data = text ? JSON.parse(text) : {};

    if (!response.ok) {
      throw new Error(data.erro || data.error || `HTTP ${response.status}`);
    }

    return data;
  }

  async function pollStatus(requestId) {
    let waitTime = 1000;
    const maxWait = 8000;
    const started = Date.now();

    while (true) {
      const data = await requestJson(`/status/${requestId}`, null, 'GET');
      const elapsed = Math.round((Date.now() - started) / 1000);
      queryStatus.textContent = JSON.stringify({
        request_id: requestId,
        elapsed_seconds: elapsed,
        payload: data,
      }, null, 2);

      if (data.status === 'COMPLETED') {
        setBadge(queryBadge, 'success', 'Concluído');

        // result pode chegar como string JSON ou como objeto
        let result = data.result;
        if (typeof result === 'string') {
          try { result = JSON.parse(result); } catch (_) { /* mantém string */ }
        }

        if (result && typeof result === 'object' && result.resposta) {
          // exibe o texto da resposta do agente
          queryResult.textContent = result.resposta;
          // atualiza o painel de status com os metadados completos
          queryStatus.textContent = JSON.stringify({
            request_id: requestId,
            status: data.status,
            completed_at: data.completed_at,
            metadata: (({ resposta, ...rest }) => rest)(result),
          }, null, 2);
        } else if (typeof result === 'string') {
          queryResult.textContent = result;
        } else {
          queryResult.textContent = JSON.stringify(result, null, 2);
        }
        return;
      }

      if (data.status === 'FAILED') {
        throw new Error(data.error || 'Processamento falhou.');
      }

      setBadge(queryBadge, 'loading', `Processando (${data.status || 'PENDING'})`);
      await new Promise((resolve) => setTimeout(resolve, waitTime));
      waitTime = Math.min(waitTime * 1.5, maxWait);
    }
  }

  queryForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setBadge(queryBadge, 'loading', 'Enviando');
    queryStatus.textContent = 'Enfileirando requisição...';
    queryResult.textContent = 'Aguardando resposta...';

    try {
      const payload = {
        pergunta: document.getElementById('pergunta').value,
        modo: document.getElementById('modo').value,
      };

      const clienteId = document.getElementById('cliente_id').value.trim();
      const clusterId = document.getElementById('cluster_id').value.trim();
      const dadosCliente = buildDadosCliente();

      if (clienteId) payload.cliente_id = clienteId;
      if (clusterId) payload.cluster_id = Number(clusterId);
      if (dadosCliente) payload.dados_cliente = dadosCliente;

      const accepted = await requestJson('/query', payload, 'POST');
      queryStatus.textContent = JSON.stringify(accepted, null, 2);
      setBadge(queryBadge, 'loading', 'Em fila');

      if (!accepted.request_id) {
        throw new Error('API não retornou request_id.');
      }

      await pollStatus(accepted.request_id);
    } catch (error) {
      setBadge(queryBadge, 'error', 'Falhou');
      queryResult.textContent = error.message;
    }
  });

  fileInput.addEventListener('change', async (event) => {
    const [file] = event.target.files;
    if (!file) return;

    try {
      const content = await file.text();
      textArea.value = content;
      if (!document.getElementById('titulo_documento').value.trim()) {
        document.getElementById('titulo_documento').value = file.name.replace(/\.[^.]+$/, '');
      }
    } catch (error) {
      uploadResult.textContent = `Falha ao ler arquivo: ${error.message}`;
      setBadge(uploadBadge, 'error', 'Falhou');
    }
  });

  uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setBadge(uploadBadge, 'loading', 'Indexando');
    uploadResult.textContent = 'Enviando documento para indexação...';

    try {
      const payload = {
        tipo: document.getElementById('tipo_documento').value,
        titulo: document.getElementById('titulo_documento').value,
        texto: textArea.value,
      };

      const clienteId = document.getElementById('upload_cliente_id').value.trim();
      const clusterId = document.getElementById('upload_cluster_id').value.trim();
      if (clienteId) payload.cliente_id = clienteId;
      if (clusterId) payload.cluster_id = Number(clusterId);

      const response = await requestJson('/documentos', payload, 'POST');
      uploadResult.textContent = JSON.stringify(response, null, 2);
      setBadge(uploadBadge, 'success', 'Indexado');
    } catch (error) {
      uploadResult.textContent = error.message;
      setBadge(uploadBadge, 'error', 'Falhou');
    }
  });

  document.getElementById('fill-sample').addEventListener('click', () => {
    document.getElementById('modo').value = 'segmento';
    document.getElementById('cliente_id').value = 'C00042';
    document.getElementById('pergunta').value = 'Que produtos de investimento devo oferecer para este cliente?';
    document.getElementById('idade').value = '55';
    document.getElementById('renda_mensal').value = '18000';
    document.getElementById('saldo_medio').value = '120000';
    document.getElementById('transacoes_mes').value = '25';
    document.getElementById('score_credito').value = '820';
    document.getElementById('num_produtos').value = '7';
    document.getElementById('canal_digital').checked = true;
    document.getElementById('inadimplente').checked = false;
  });

  document.getElementById('fill-document').addEventListener('click', () => {
    document.getElementById('tipo_documento').value = 'documento';
    document.getElementById('titulo_documento').value = 'Politica de investimentos 2026';
    textArea.value = [
      'Clientes conservadores priorizam liquidez, previsibilidade e proteção contra inflação.',
      'Ofertas recomendadas: Tesouro Selic, CDB com liquidez diária e fundos DI com baixa taxa.',
      'Perfis de alta renda com horizonte de longo prazo podem receber alocação gradual em NTN-B e debêntures incentivadas.'
    ].join('\n\n');
  });
})();