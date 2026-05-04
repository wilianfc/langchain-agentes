param(
  [ValidateSet("validate", "plan", "apply")]
  [string]$Mode = "validate"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $Root
$PluginDir = Join-Path $RepoRoot "infraestrutura/.terraform/providers"
$SharedDataDir = Join-Path $Root ".tfdata_shared"
New-Item -ItemType Directory -Force -Path $SharedDataDir | Out-Null
$Order = @(
  "aws_dynamodb",
  "aws_sqs",
  "aws_sns",
  "aws_s3",
  "aws_vpc_endpoints",
  "aws_secrets",
  "aws_iam",
  "aws_lambda_layer",
  "aws_opensearch",
  "aws_neptune",
  "aws_neptune_proxy",
  "aws_neptune_replication",
  "aws_lambda_worker",
  "aws_api_gateway",
  "aws_cloudfront_frontend"
)

foreach ($stack in $Order) {
  $path = Join-Path $Root $stack
  $env:TF_DATA_DIR = Join-Path $SharedDataDir $stack
  Write-Host "=== [$Mode] $stack ==="
  terraform "-chdir=$path" init -backend=false -input=false -no-color "-plugin-dir=$PluginDir" | Out-Null

  if ($Mode -eq "validate") {
    terraform "-chdir=$path" validate -no-color
  } elseif ($Mode -eq "plan") {
    terraform "-chdir=$path" plan -input=false -no-color
  } else {
    terraform "-chdir=$path" apply -auto-approve -input=false -no-color
  }
}
