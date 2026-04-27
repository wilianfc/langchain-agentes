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

resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.archive_file.layer.output_path
  layer_name          = "${var.project_name}-dependencies-${var.environment}"
  compatible_runtimes = ["python3.11"]
  source_code_hash    = data.archive_file.layer.output_base64sha256
}
