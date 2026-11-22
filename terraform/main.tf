# 1. TERRAFORM BLOCK: which providers (plugins) Terraform needs and which versions.
#    "~> 5.0" means any 5.x release, but not 6.0. Versions get locked in .terraform.lock.hcl.
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# 2. PROVIDER BLOCK: how to talk to AWS. Everything is created in eu-north-1 (Stockholm).
#    Credentials are not here; they come from ~/.aws/credentials or environment variables.
provider "aws" {
  region = "eu-north-1"
}

# 3. DATA SOURCE: READ-ONLY lookup of the AZs available in this region.
#    Nothing is created. Used below so we don't hardcode AZ names.
data "aws_availability_zones" "available" {}

# 4. VPC MODULE: a ready-made community module that builds the network.
#    Creates the VPC, subnets, route tables, Internet Gateway and NAT Gateway.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "confine-vpc"
  cidr = "10.0.0.0/16" # the VPC's whole private IP range (~65k addresses)

  # Use the first 2 AZs so the cluster survives one AZ failing.
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # One subnet per AZ. Private: worker nodes live here, no direct inbound internet.
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  # Public: route to the Internet Gateway; later used for load balancers (ALB) and the NAT.
  public_subnets = ["10.0.101.0/24", "10.0.102.0/24"]

  # NAT Gateway lets private nodes reach out (pull images, updates) without being reachable.
  enable_nat_gateway = true
  # One shared NAT instead of one per AZ: cheaper, but not highly available. Bills hourly.
  single_nat_gateway = true
}

# 5. EKS MODULE: creates the managed Kubernetes cluster (control plane run by AWS),
#    plus the IAM roles, security groups and worker node group it needs.
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "confine"
  cluster_version = "1.31" # Kubernetes version; EKS retires old versions, so check it's supported

  # Reference to module outputs -> implicit dependency: the VPC is created first.
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets # nodes and the cluster network interfaces go in private subnets

  # Lets you run kubectl from your laptop. Open to the internet; restrict for real use.
  cluster_endpoint_public_access = true
  # Gives the IAM user that runs terraform apply admin rights inside the cluster.
  enable_cluster_creator_admin_permissions = true

  # Managed node group: AWS provisions and updates the EC2 worker nodes for you.
  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.small"] # small and cheap; limited pods per node
      min_size       = 1            # autoscaling floor
      max_size       = 3            # autoscaling ceiling
      desired_size   = 2            # starts with 2 nodes
    }
  }
}

# 6. OUTPUT: printed after apply. Use it with:
#    aws eks update-kubeconfig --name confine --region eu-north-1
output "cluster_name" {
  value = module.eks.cluster_name
}