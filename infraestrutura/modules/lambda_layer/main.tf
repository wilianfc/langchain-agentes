# Instala dependências Python com wheels compatíveis com Linux (Lambda)
resource "null_resource" "pip_install" {
  triggers = {
    requirements = filemd5("${path.module}/requirements.txt")
    platform     = "manylinux2014_x86_64"
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      Remove-Item -Recurse -Force "${path.module}/layer_content/python" -ErrorAction SilentlyContinue
      New-Item -ItemType Directory -Force -Path "${path.module}/layer_content/python" | Out-Null
      pip install -r "${path.module}/requirements.txt" `
        -t "${path.module}/layer_content/python" `
        --platform manylinux2014_x86_64 `
        --implementation cp `
        --python-version 3.11 `
        --only-binary=:all: `
        --upgrade `
        --quiet
    EOT
  }
}

data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.module}/layer_content"
  output_path = "${path.module}/dist/layer.zip"
  depends_on  = [null_resource.pip_install]
}

# Upload via S3 — necessário para layers > 50 MB (limite do upload direto é 50 MB)
resource "aws_s3_object" "layer_zip" {
  bucket = var.s3_bucket_name
  key    = "lambda-layer/layer.zip"
  source = data.archive_file.layer.output_path
  etag   = data.archive_file.layer.output_base64sha256

  depends_on = [data.archive_file.layer]
}

resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.project_name}-dependencies-${var.environment}"
  compatible_runtimes = ["python3.11"]
  s3_bucket           = aws_s3_object.layer_zip.bucket
  s3_key              = aws_s3_object.layer_zip.key
  source_code_hash    = data.archive_file.layer.output_base64sha256

  depends_on = [aws_s3_object.layer_zip]
}
