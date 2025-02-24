locals {
  organization = "logikal.io"
  project = "stormware"
  backend = "gcs"

  providers = {
    google = {
      version = "~> 6.19"
      region = "europe-west6"
    }
    aws = {
      version = "~> 5.31"
      region = "eu-central-2"
    }
  }
}
