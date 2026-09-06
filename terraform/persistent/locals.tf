locals {
  services = ["auth", "product", "order", "payment", "notification"]
  envs     = ["dev", "prod"]
  service_env = {
    for pair in setproduct(local.envs, local.services) :
    "${pair[0]}-${pair[1]}" => { env = pair[0], svc = pair[1] }
  }

  github_repo             = "ismaelyasindev/b2b-eks-platform"
  tfstate_bucket          = "b2b-eks-platform-tfstate-london"
  tfstate_lock_table      = "b2b-eks-platform-tfstate-lock"
  bedrock_model_id        = "anthropic.claude-3-haiku-20240307-v1:0"
  github_oidc_thumbprints = ["6938fd4d98bab03faadb97b34396831e3780aea3", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]

  github_oidc_subs = {
    ecr-push        = "repo:${local.github_repo}:*"
    tf-plan         = "repo:${local.github_repo}:*"
    tf-apply        = "repo:${local.github_repo}:ref:refs/heads/main"
    tf-destroy      = "repo:${local.github_repo}:ref:refs/heads/main"
    frontend-deploy = "repo:${local.github_repo}:*"
  }
}
