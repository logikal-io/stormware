locals {
  state_backend = "gcs"
  organization = "logikal.io"
  project = "stormware"

  providers = {
    google = {
      version = "~> 7.11"
      region = "europe-west6"
    }
    aws = {
      version = "~> 6.20"
      region = "eu-central-2"
    }
  }

  modules = {
    "github.com/logikal-io/terraform-modules" = "v2.4.0"
  }
}
