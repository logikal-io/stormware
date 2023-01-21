output "gcp_testing_workload_identity_provider" {
  description = "The full identifier of the GitHub workload identity pool provider"
  value = module.gcp_github_auth.workload_identity_provider
}

output "gcp_testing_service_account" {
  description = "The email of the Google Cloud service account used for running tests"
  value = module.gcp_github_auth.service_account_emails["testing"]
}

output "aws_testing_role" {
  description = "The ARN of the AWS role used for running tests"
  value = module.aws_github_auth.iam_role_arns["testing"]
}

output "google_secret_manager_test_key" {
  description = "The Google Cloud Secret Manager key to use in tests"
  value = google_secret_manager_secret.test.secret_id
}

output "aws_secrets_manager_test_key" {
  description = "The AWS Secrets Manager key to use in tests"
  value = aws_secretsmanager_secret.test.name
}

output "google_bigquery_test_dataset" {
  description = "The BigQuery dataset to use in tests"
  value = google_bigquery_dataset.test.dataset_id
}
