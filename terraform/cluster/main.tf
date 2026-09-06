module "vpc" {
  source = "../modules/vpc"

  cluster_name       = var.cluster_name
  vpc_cidr           = var.vpc_cidr
  azs                = local.azs
  deploy_nat_gateway = var.deploy_nat_gateway
}

module "eks" {
  source = "../modules/eks"

  cluster_name       = var.cluster_name
  cluster_version    = var.cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_count         = var.node_count
}

module "storage" {
  source = "../modules/storage_monitoring"

  cluster_name = module.eks.cluster_name

  depends_on = [module.eks]
}

module "rds" {
  source = "../modules/rds"

  cluster_name               = var.cluster_name
  vpc_id                     = module.vpc.vpc_id
  private_subnet_ids         = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.eks.node_security_group_id, module.eks.cluster_security_group_id]
  instance_classes           = local.rds_instance_class
}

module "sqs" {
  source = "../modules/sqs"

  cluster_name = var.cluster_name
}

module "waf" {
  source = "../modules/waf"
}

data "aws_caller_identity" "current" {}

module "pod_identity" {
  source = "../modules/pod_identity"

  cluster_name       = module.eks.cluster_name
  envs               = local.envs
  service_env        = local.service_env
  db_secret_arns     = data.terraform_remote_state.persistent.outputs.db_secret_arns
  sns_topic_arn      = data.terraform_remote_state.persistent.outputs.sns_aiops_topic_arn
  sqs_queue_arn      = module.sqs.queue_arn
  sqs_dlq_arn        = module.sqs.dlq_arn
  throttle_table_arn = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${data.terraform_remote_state.persistent.outputs.throttle_table_name}"

  depends_on = [module.eks]
}

module "karpenter" {
  source = "../modules/karpenter"

  cluster_name     = module.eks.cluster_name
  cluster_endpoint = module.eks.cluster_endpoint
  node_role_arn    = module.eks.node_role_arn
  node_role_name   = module.eks.node_role_name

  depends_on = [module.eks]
}

module "bootstrap" {
  source = "../modules/bootstrap"

  cluster_name = module.eks.cluster_name
  vpc_id       = module.vpc.vpc_id

  depends_on = [module.eks]
}

module "cloudfront_frontend" {
  count  = var.api_origin_domain == "" ? 0 : 1
  source = "../modules/cloudfront_frontend"

  api_origin_domain                      = var.api_origin_domain
  storefront_bucket                      = data.terraform_remote_state.persistent.outputs.storefront_bucket
  storefront_bucket_regional_domain_name = data.terraform_remote_state.persistent.outputs.storefront_bucket_regional_domain_name
}
