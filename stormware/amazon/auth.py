from configparser import ConfigParser
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, Set

from boto3.session import Session

from stormware.auth import Auth

logger = getLogger(__name__)


class AWSAuth(Auth):
    def __init__(self, *args: Any, credentials: Path = Path('~/.aws/credentials'), **kwargs: Any):
        """
        Amazon Web Services authentication manager.

        Attributes:
            profiles (Set[str]): The available named profiles.

        """
        super().__init__(*args, **kwargs)

        self.profiles: Set[str] = set()
        credentials = credentials.expanduser()
        if credentials.exists():
            config = ConfigParser()
            config.read(credentials)
            self.profiles = set(config.sections())
        else:
            logger.debug(f'Named profile credentials file "{credentials}" does not exist')

    def session(self, organization: Optional[str] = None, region: Optional[str] = None) -> Session:
        """
        Return a session that uses the organization ID named profile credentials (if it exists).
        """
        organization_id = self.organization_id(organization=organization)
        profile = organization_id if organization_id in self.profiles else None
        if profile:
            logger.debug(f'Using named profile "{profile}"')
        return Session(profile_name=profile, region_name=region)
