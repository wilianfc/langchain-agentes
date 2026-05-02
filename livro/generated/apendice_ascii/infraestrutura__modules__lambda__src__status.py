import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["DYNAMODB_TABLE"]


def lambda_handler(event, context):
    request_id = (event.get("pathParameters") or {}).get("request_id")

    if not request_id:
        return _response(400, {"error": "request_id e obrigatorio"})

    item = dynamodb.Table(TABLE_NAME).get_item(
        Key={"request_id": request_id}
    ).get("Item")

    if not item:
        return _response(404, {"error": "request_id nao encontrado"})

    resposta = {
        "request_id": item["request_id"],
        "status": item["status"],
        "criado_em": item.get("criado_em"),
        "atualizado_em": item.get("atualizado_em"),
    }

    if item["status"] == "COMPLETED":
        resposta["resultado"] = item.get("resultado")

    if item["status"] == "FAILED":
        resposta["erro"] = item.get("erro", "Erro desconhecido")

    return _response(200, resposta)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
