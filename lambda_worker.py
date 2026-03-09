"""
Lambda Worker - Processa mensagens da fila SQS de forma assíncrona
===================================================================

Consome mensagens do SQS, executa o agente LangChain (até 15min),
atualiza status no DynamoDB e notifica via SNS.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Importar o pipeline existente
from aws_pipeline_clientes import _get_pipeline, FEATURES

# Clientes AWS
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Variáveis de ambiente
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
table = dynamodb.Table(DYNAMODB_TABLE)


def update_status(request_id: str, status: str, **kwargs):
    """Atualiza status no DynamoDB"""
    update_expr = "SET #status = :status, updated_at = :updated"
    expr_values = {
        ':status': status,
        ':updated': datetime.utcnow().isoformat()
    }
    expr_names = {'#status': 'status'}
    
    # Adicionar campos extras (error, result, etc.)
    for key, value in kwargs.items():
        update_expr += f", {key} = :{key}"
        expr_values[f':{key}'] = value
    
    table.update_item(
        Key={'request_id': request_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values
    )


def notify_completion(request_id: str, status: str, result: Dict = None):
    """Envia notificação via SNS (opcional)"""
    if not SNS_TOPIC_ARN:
        return
    
    try:
        message = {
            'request_id': request_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        if result:
            message['result'] = result
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f'Processamento {status}: {request_id}',
            Message=json.dumps(message, ensure_ascii=False)
        )
    except Exception as e:
        print(f"Erro ao enviar notificação SNS: {e}")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Entry point para SQS trigger.
    
    Processa cada mensagem da fila:
    1. Atualiza status para PROCESSING
    2. Executa o pipeline LangChain
    3. Salva resultado no DynamoDB
    4. Notifica via SNS (se configurado)
    5. Retorna sucesso (mensagem deletada da fila)
    """
    
    # Pipeline carregado no cold start (reutilizado entre invocações)
    pipeline = _get_pipeline()
    
    # SQS envia batch de mensagens
    for record in event['Records']:
        request_id = None
        try:
            # Parse mensagem
            body = json.loads(record['body'])
            request_id = body['request_id']
            cliente_id = body['cliente_id']
            dados_cliente = body['dados_cliente']
            pergunta = body['pergunta']
            modo = body.get('modo', 'segmento')
            cluster_id = body.get('cluster_id')
            
            print(f"[{request_id}] Iniciando processamento em modo '{modo}'")
            
            # Validar campos
            if modo != 'persona':
                ausentes = set(FEATURES) - set(dados_cliente.keys())
                if ausentes:
                    raise ValueError(f"Campos ausentes em dados_cliente: {ausentes}")
            
            # Atualizar status: PROCESSING
            update_status(request_id, 'PROCESSING', 
                         cliente_id=cliente_id,
                         started_at=datetime.utcnow().isoformat())
            
            # Executar pipeline (pode levar minutos!)
            if modo == 'persona':
                if cluster_id is None and dados_cliente is None:
                    raise ValueError("Modo 'persona' requer 'cluster_id' ou 'dados_cliente'")
                resultado = pipeline.responder_como_persona(
                    pergunta,
                    cluster_id=int(cluster_id) if cluster_id is not None else None,
                    dados_cliente=dados_cliente
                )
            elif modo == 'twin':
                resultado = pipeline.responder_como_twin(cliente_id, dados_cliente, pergunta)
            else:  # segmento
                resultado = pipeline.responder(cliente_id, dados_cliente, pergunta)
            
            print(f"[{request_id}] Processamento concluído com sucesso")
            
            # Atualizar status: COMPLETED
            update_status(request_id, 'COMPLETED',
                         result=resultado,
                         completed_at=datetime.utcnow().isoformat())
            
            # Notificar conclusão
            notify_completion(request_id, 'COMPLETED', resultado)
        
        except ValueError as e:
            error_msg = f"Erro de validação: {str(e)}"
            print(f"[{request_id}] {error_msg}")
            if request_id:
                update_status(request_id, 'FAILED', error=error_msg)
                notify_completion(request_id, 'FAILED')
        
        except Exception as e:
            error_msg = f"Erro inesperado: {str(e)}"
            print(f"[{request_id}] {error_msg}")
            if request_id:
                update_status(request_id, 'FAILED', error=error_msg)
                notify_completion(request_id, 'FAILED')
            # Re-raise para que o SQS reprocesse (retry automático)
            raise
    
    return {'statusCode': 200, 'body': 'Processamento concluído'}
