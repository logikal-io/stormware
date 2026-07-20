from logikal_utils.project import project_name, tool_config


class Auth:
    def __init__(self, organization: str | None = None):
        self._organization = organization

    def organization(self, organization: str | None = None) -> str:
        """
        Return the organization name.

        Defaults to the ``organization`` value set in ``pyproject.toml`` under the
        ``tool.stormware`` section.
        """
        organization = (
            organization or self._organization
            or tool_config('stormware').get('organization')
        )
        if not organization:
            raise ValueError('You must provide an organization')
        return organization

    def organization_id(self, organization: str | None = None) -> str:
        """
        Return the organization ID.

        The organization ID is derived from the organization name by replacing dots with dashes.
        """
        return self.organization(organization).replace('.', '-')


class ProjectAuth(Auth):
    def __init__(self, organization: str | None = None, project: str | None = None):
        super().__init__(organization=organization)
        self._project = project

    def project(self, project: str | None = None) -> str:
        """
        Return the project name.

        Defaults to the ``project`` value set in ``pyproject.toml`` under the ``tool.stormware``
        section or the ``name`` value set under the ``project`` section.
        """
        project = (
            project or self._project
            or tool_config('stormware').get('project')
            or project_name(raise_error_on_missing=False)
        )
        if not project:
            raise ValueError('You must provide a project')
        return project

    def project_id(self, organization: str | None = None, project: str | None = None) -> str:
        """
        Return the project ID.

        The project ID is constructed as ``{project}-{organization_id}``.
        """
        return f'{self.project(project=project)}-{self.organization_id(organization)}'
