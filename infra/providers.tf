terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.21"
    }
    docker = {
      source  = "registry.opentofu.org/kreuzwerker/docker"
      version = "~> 3.9"
    }
  }
}

provider "aws" {
  region = local.region
}

provider "docker" {
  host = "tcp://172.27.39.22:2376"
}