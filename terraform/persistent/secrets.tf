resource "aws_secretsmanager_secret" "db" {
  for_each = local.service_env

  name                    = "b2b/${each.value.env}/${each.value.svc}/db"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret" "postgres_exporter" {
  for_each = toset(local.envs)

  name                    = "b2b/${each.value}/monitoring/postgres-exporter"
  recovery_window_in_days = 0
}
