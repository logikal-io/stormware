locals {
  organization = "logikal.io"
  project = "stormware"
  backend = "gcs"

  providers = {
    google = {
      version = "~> 5.9"
      region = "europe-west6"
    }
    aws = {
      version = "~> 5.31"
      region = "eu-central-2"
    }
  }
}
