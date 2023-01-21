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
    testing = ["logikal-io/mindlab"]
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
