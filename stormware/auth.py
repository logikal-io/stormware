from logikal_utils.project import tool_config


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
