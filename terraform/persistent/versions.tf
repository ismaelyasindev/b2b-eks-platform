terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "b2b-eks-platform-tfstate-london"
    key            = "persistent/terraform.tfstate"
    region         = "eu-west-2"
    dynamodb_table = "b2b-eks-platform-tfstate-lock"
    encrypt        = true
  }
}
