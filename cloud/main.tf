# Services
resource "google_project_service" "secret_manager" {
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "sheets" {
  service = "sheets.googleapis.com"
}

resource "google_project_service" "bigquery" {
  service = "bigquery.googleapis.com"
}

# GitHub Actions
module "gcp_github_auth" {
  source = "github.com/logikal-io/terraform-modules//gcp/github-auth?ref=v1.2.0"

  service_account_accesses = {
    testing = ["logikal-io/stormware"]
  }
}

module "aws_github_auth" {
  source = "github.com/logikal-io/terraform-modules//aws/github-auth?ref=v1.2.0"

  project_id = var.project_id
  role_accesses = {
    testing = ["logikal-io/stormware"]
  }
}

# Testing
resource "google_secret_manager_secret" "test" {
  secret_id = "stormware-test"
  replication {
    automatic = true
  }

  depends_on = [google_project_service.secret_manager]
}

resource "aws_secretsmanager_secret" "test" {
  name = "stormware-test"
  recovery_window_in_days = 0
}

resource "google_bigquery_dataset" "test" {
  dataset_id = "test"
  description = "Tables used for testing"
  location = "EU"

  depends_on = [google_project_service.bigquery]
}

# Permissions
resource "google_project_iam_member" "secret_adder" {
  project = var.project_id
  role = "roles/secretmanager.secretVersionAdder"
  member = "serviceAccount:${module.gcp_github_auth.service_account_emails["testing"]}"

  condition {
    title = "test secret"
    expression = "resource.name == '${google_secret_manager_secret.test.name}'"
  }
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${module.gcp_github_auth.service_account_emails["testing"]}"

  condition {
    title = "test secret"
    expression = "resource.name == '${google_secret_manager_secret.test.name}'"
  }
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role = "roles/bigquery.jobUser"
  member = "serviceAccount:${module.gcp_github_auth.service_account_emails["testing"]}"
}

data "aws_iam_policy_document" "test_secret_access" {
  version = "2012-10-17"

  statement {
    actions = ["secretsmanager:PutSecretValue", "secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.test.arn]
  }
}

resource "aws_iam_policy" "test_secret_access" {
  name = "test-secret-access"
  policy = data.aws_iam_policy_document.test_secret_access.json
}

resource "aws_iam_role_policy_attachment" "test_secret_access" {
  role = module.aws_github_auth.iam_role_names["testing"]
  policy_arn = aws_iam_policy.test_secret_access.arn
}
