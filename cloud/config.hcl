locals {
  state_backend = "gcs"
  organization = "logikal.io"
  project = "stormware"

  providers = {
    google = {
      version = "~> 7.34"
      region = "europe-west6"
    }
    aws = {
      version = "~> 6.47"
      region = "eu-central-2"
    }
  }

  modules = {
    "github.com/logikal-io/terraform-modules" = "v5.3.1"
  }
}
