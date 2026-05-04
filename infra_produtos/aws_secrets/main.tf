module "product" {
  source = "../../infraestrutura/modules/secrets"
  anthropic_api_key = var.anthropic_api_key
}

