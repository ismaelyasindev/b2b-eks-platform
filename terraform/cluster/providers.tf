variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "cluster_name" {
  type    = string
  default = "b2b-eks-platform"
}

variable "cluster_version" {
  type    = string
  default = "1.33"
}

variable "deploy_nat_gateway" {
  type    = bool
  default = true
}

variable "node_count" {
  type    = number
  default = 1
}

variable "api_origin_domain" {
  type    = string
  default = ""
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

locals {
  services = ["auth", "product", "order", "payment", "notification"]
  envs     = ["dev", "prod"]
  service_env = {
    for pair in setproduct(local.envs, local.services) :
    "${pair[0]}-${pair[1]}" => { env = pair[0], svc = pair[1] }
  }

  rds_instance_class = {
    dev  = "db.t4g.micro"
    prod = "db.t4g.small"
  }

  azs = ["${var.region}a", "${var.region}b"]
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "b2b-eks-platform"
      Environment = "multi-tenant-cluster"
      ManagedBy   = "terraform"
      CostCenter  = "platform-engineering"
      Layer       = "cluster"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
    }
  }
}
