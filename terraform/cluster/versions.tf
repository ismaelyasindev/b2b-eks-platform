terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket         = "b2b-eks-platform-tfstate-london"
    key            = "cluster/terraform.tfstate"
    region         = "eu-west-2"
    dynamodb_table = "b2b-eks-platform-tfstate-lock"
    encrypt        = true
  }
}
