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

resource "google_project_service" "drive" {
  service = "drive.googleapis.com"
}

# GitHub Actions
module "gcp_github_auth" {
  source = "github.com/logikal-io/terraform-modules//gcp/github-auth?ref=v1.15.0"

  github_organization = var.organization_id
  service_account_accesses = {
    testing = ["logikal-io/stormware"]
  }
}

module "aws_github_auth" {
  source = "github.com/logikal-io/terraform-modules//aws/github-auth?ref=v1.15.0"

  project_id = var.project_id
  role_accesses = {
    testing = ["logikal-io/stormware"]
  }
}

# Testing
resource "google_secret_manager_secret" "test" {
  secret_id = "stormware-test"
  replication {
    auto {}
  }

  depends_on = [google_project_service.secret_manager]
}

resource "google_secret_manager_secret" "facebook" {
  secret_id = "stormware-facebook"
  replication {
    auto {}
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
locals {
  service_accounts = toset([
    module.gcp_github_auth.service_account_emails["testing"],
    "docs-uploader@docs-logikal-io.iam.gserviceaccount.com",
  ])
}

resource "google_secret_manager_secret_iam_member" "test_accessor" {
  secret_id = google_secret_manager_secret.test.id
  role = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${module.gcp_github_auth.service_account_emails["testing"]}"
}

resource "google_secret_manager_secret_iam_member" "facebook_accessor" {
  for_each = local.service_accounts

  secret_id = google_secret_manager_secret.facebook.id
  role = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${each.key}"
}

resource "google_project_iam_member" "bigquery_job_user" {
  for_each = local.service_accounts

  project = var.project_id
  role = "roles/bigquery.jobUser"
  member = "serviceAccount:${each.key}"
}

resource "google_project_iam_member" "bigquery_read_session_user" {
  for_each = local.service_accounts

  project = var.project_id
  role = "roles/bigquery.readSessionUser"
  member = "serviceAccount:${each.key}"
}

resource "google_bigquery_dataset_access" "test" {
  for_each = local.service_accounts

  dataset_id = google_bigquery_dataset.test.dataset_id
  role = "roles/bigquery.dataEditor"
  user_by_email = each.key
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
