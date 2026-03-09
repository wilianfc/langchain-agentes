"""
Lambda Status - Consulta status e resultado do processamento
=============================================================

Endpoint: GET /status/{request_id}
Permite que o cliente faça polling para verificar o progresso.
"""

import json
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Cliente AWS
dynamodb = boto3.resource('dynamodb')

# Variáveis de ambiente
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Entry point para API Gateway (GET /status/{request_id}).
    
    Entrada:
      GET /status/req_abc123def456
    
    Saída (PENDING):
      {
        "statusCode": 200,
        "body": {
          "request_id": "req_abc123def456",
          "status": "PENDING",
          "message": "Aguardando processamento"
        }
      }
    
    Saída (PROCESSING):
      {
        "statusCode": 200,
        "body": {
          "request_id": "req_abc123def456",
          "status": "PROCESSING",
          "message": "Processamento em andamento",
          "started_at": "2026-03-09T10:30:00"
        }
      }
    
    Saída (COMPLETED):
      {
        "statusCode": 200,
        "body": {
          "request_id": "req_abc123def456",
          "status": "COMPLETED",
          "result": {
            "cliente_id": "C12345",
            "cluster_id": 2,
            "segmento": "Massa Estável",
            "resposta": "..."
          },
          "completed_at": "2026-03-09T10:32:15"
        }
      }
    
    Saída (FAILED):
      {
        "statusCode": 200,
        "body": {
          "request_id": "req_abc123def456",
          "status": "FAILED",
          "error": "Erro durante processamento: ...",
          "created_at": "2026-03-09T10:30:00"
        }
      }
    
    Saída (NOT_FOUND):
      {
        "statusCode": 404,
        "body": {
          "error": "request_id não encontrado"
        }
      }
    """
    try:
        # Extrair request_id do path
        request_id = event.get('pathParameters', {}).get('request_id')
        
        if not request_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'request_id é obrigatório'
                })
            }
        
        # Buscar no DynamoDB
        response = table.get_item(Key={'request_id': request_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'request_id não encontrado',
                    'request_id': request_id
                })
            }
        
        item = response['Item']
        status = item['status']
        
        # Montar resposta baseada no status
        response_body = {
            'request_id': request_id,
            'status': status,
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at')
        }
        
        if status == 'PENDING':
            response_body['message'] = 'Aguardando processamento na fila'
        
        elif status == 'PROCESSING':
            response_body['message'] = 'Processamento em andamento'
            response_body['started_at'] = item.get('started_at')
        
        elif status == 'COMPLETED':
            response_body['message'] = 'Processamento concluído com sucesso'
            response_body['result'] = item.get('result', {})
            response_body['completed_at'] = item.get('completed_at')
        
        elif status == 'FAILED':
            response_body['message'] = 'Processamento falhou'
            response_body['error'] = item.get('error', 'Erro desconhecido')
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache'  # Evitar cache para polling
            },
            'body': json.dumps(response_body, ensure_ascii=False)
        }
    
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Erro ao consultar status',
                'details': str(e)
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Erro interno',
                'details': str(e)
            })
        }
