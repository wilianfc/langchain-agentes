"""
Lambda proxy: recebe {"cypher": "..."} e retorna lista de resultados do Neptune.
Deve estar na VPC para acessar Neptune (VPC-only).
"""
import json
import os

import boto3
import botocore.auth
import botocore.awsrequest
import requests

NEPTUNE_ENDPOINT = os.environ["NEPTUNE_ENDPOINT"]
AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")


def _query(cypher: str) -> list:
    url = f"https://{NEPTUNE_ENDPOINT}:8182/openCypher"
    body = json.dumps({"query": cypher}).encode("utf-8")
    creds = boto3.session.Session().get_credentials()
    aws_req = botocore.awsrequest.AWSRequest(
        method="POST", url=url, data=body,
        headers={"Content-Type": "application/json", "Host": f"{NEPTUNE_ENDPOINT}:8182"},
    )
    botocore.auth.SigV4Auth(creds, "neptune-db", AWS_REGION).add_auth(aws_req)
    resp = requests.post(url, data=body, headers=dict(aws_req.headers), timeout=15)
    resp.raise_for_status()
    return resp.json().get("results", [])


def lambda_handler(event, context):
    return _query(event["cypher"])
