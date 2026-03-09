"""
Lambda Controller - Recebe requisições e enfileira no SQS
==========================================================

Retorna request_id imediatamente para o cliente (< 1s).
Integração com API Gateway para evitar timeout de 30s.
"""

import json
import uuid
import os
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Clientes AWS
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Variáveis de ambiente
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Entry point para API Gateway.
    
    Entrada:
      POST /query
      {
        "cliente_id": "C12345",
        "dados_cliente": {...},
        "pergunta": "Quais produtos você recomenda?",
        "modo": "segmento"
      }
    
    Saída (imediata, < 1s):
      {
        "statusCode": 202,
        "body": {
          "request_id": "req_abc123def456",
          "status": "PENDING",
          "message": "Processamento iniciado. Consulte /status/{request_id}"
        }
      }
    """
    try:
        # Parse body (se vier do API Gateway)
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        # Gerar request_id único
        request_id = f"req_{uuid.uuid4().hex}"
        timestamp = datetime.utcnow().isoformat()
        
        # Validações básicas
        modo = body.get('modo', 'segmento')
        
        # Modo persona aceita cluster_id OU dados_cliente
        if modo == 'persona':
            if 'cluster_id' not in body and 'dados_cliente' not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': "Modo 'persona' requer 'cluster_id' ou 'dados_cliente'"
                    })
                }
            required_fields = ['pergunta']
        else:
            required_fields = ['cliente_id', 'dados_cliente', 'pergunta']
        
        missing = [f for f in required_fields if f not in body]
        if missing:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Campos obrigatórios ausentes: {missing}'
                })
            }
        
        # 1. Salvar status inicial no DynamoDB (PENDING)
        table.put_item(
            Item={
                'request_id': request_id,
                'status': 'PENDING',
                'cliente_id': body['cliente_id'],
                'modo': body.get('modo', 'segmento'),
                'created_at': timestamp,
                'updated_at': timestamp,
                'ttl': int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60)  # 7 dias
            }
        )
        
        # 2. Enfileirar mensagem no SQS
        message_body = {
            'request_id': request_id,
            'cliente_id': body['cliente_id'],
            'dados_cliente': body['dados_cliente'],
            'pergunta': body['pergunta'],
            'modo': body.get('modo', 'segmento'),
            'cluster_id': body.get('cluster_id')  # Para modo persona
        }
        
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'request_id': {
                    'StringValue': request_id,
                    'DataType': 'String'
                }
            }
        )
        
        # 3. Retornar request_id imediatamente
        return {
            'statusCode': 202,  # Accepted
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'request_id': request_id,
                'status': 'PENDING',
                'message': f'Processamento iniciado. Consulte GET /status/{request_id}',
                'estimated_time': '30-120 segundos'
            })
        }
    
    except KeyError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Campo obrigatório ausente: {str(e)}'})
        }
    
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Erro ao iniciar processamento',
                'details': str(e)
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Erro interno',
                'details': str(e)
            })
        }
