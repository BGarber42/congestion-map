locals {
  region = "us-east-1"
  name   = "congestion"

  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)
}