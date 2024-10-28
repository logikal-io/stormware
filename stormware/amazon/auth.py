from configparser import ConfigParser
from logging import getLogger
from pathlib import Path
from typing import Any

from boto3.session import Session

from stormware.auth import Auth

logger = getLogger(__name__)


class AWSAuth(Auth):
    def __init__(self, *args: Any, credentials: Path = Path('~/.aws/credentials'), **kwargs: Any):
        """
        Amazon Web Services authentication manager.

        Attributes:
            profiles (set[str]): The available named profiles.

        """
        super().__init__(*args, **kwargs)

        self.profiles: set[str] = set()
        credentials = credentials.expanduser()
        if credentials.exists():
            config = ConfigParser()
            config.read(credentials)
            self.profiles = set(config.sections())
        else:
            logger.debug(f'Named profile credentials file "{credentials}" does not exist')

    def profile(self, organization: str | None = None) -> str | None:
        """
        Return the profile name (same as the organization ID) or :data:`None` if it does not exist.
        """
        organization_id = self.organization_id(organization=organization)
        if (profile := organization_id if organization_id in self.profiles else None):
            logger.debug(f'Using named profile "{profile}"')
        return profile

    def session(self, organization: str | None = None, region: str | None = None) -> Session:
        """
        Return a session that uses named profile credentials (if it exists).
        """
        return Session(profile_name=self.profile(organization=organization), region_name=region)
