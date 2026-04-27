import json
import uuid
import boto3
import os
from datetime import datetime, timezone

import botocore.exceptions
from botocore.config import Config

_config = Config(connect_timeout=5, read_timeout=10)

dynamodb = boto3.resource("dynamodb", config=_config)
sqs = boto3.client("sqs", config=_config)

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"error": "Body inválido"})

    pergunta = body.get("pergunta")
    if not pergunta:
        return _response(400, {"error": "Campo 'pergunta' é obrigatório"})

    modo = body.get("modo", "segmento")
    cliente_id = body.get("cliente_id", "")
    dados_cliente = body.get("dados_cliente", body.get("dados", {}))

    request_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()

    dynamodb.Table(TABLE_NAME).put_item(Item={
        "request_id": request_id,
        "status": "PENDING",
        "pergunta": pergunta,
        "modo": modo,
        "cliente_id": cliente_id,
        "criado_em": agora,
        "atualizado_em": agora,
        "ttl": int(datetime.now(timezone.utc).timestamp()) + 86400,
    })

    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({
                "request_id": request_id,
                "pergunta": pergunta,
                "modo": modo,
                "cliente_id": cliente_id,
                "dados_cliente": dados_cliente,
            }),
        )
    except botocore.exceptions.ClientError as exc:
        return _response(503, {"error": f"Falha ao enfileirar requisição: {exc.response['Error']['Code']}"})

    return _response(202, {
        "request_id": request_id,
        "status": "PENDING",
        "mensagem": "Requisição enfileirada. Use o request_id para consultar o status.",
    })


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
