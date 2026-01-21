output "gcp_testing_workload_identity_provider" {
  value = module.gcp_github_auth.workload_identity_provider
}

output "gcp_testing_service_account" {
  value = module.gcp_github_auth.service_account_emails["testing"]
}

output "aws_testing_role" {
  value = module.aws_github_auth.iam_role_arns["testing"]
}

output "google_secret_manager_test_key" {
  value = google_secret_manager_secret.test.secret_id
}

output "aws_secrets_manager_test_key" {
  value = aws_secretsmanager_secret.test.name
}

output "google_bigquery_test_dataset" {
  value = google_bigquery_dataset.test.dataset_id
}
