include "commons" {
  path = pathexpand("~/.terragrunt/commons.hcl")
  expose = true
}

inputs = {
  project_id = include.commons.locals.project_id
  organization_id = include.commons.locals.organization_id
}
