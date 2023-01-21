from configparser import ConfigParser
from logging import getLogger
from pathlib import Path
from typing import Optional

from boto3.session import Session

from stormware.auth import Auth

logger = getLogger(__name__)


class AWSAuth(Auth):
    """
    Amazon Web Services authentication manager.
    """
    def profile_exists(self, name: str, credentials: Path = Path('~/.aws/credentials')) -> bool:
        """
        Return :data:`True` if the given named profile credentials exist.
        """
        credentials = credentials.expanduser()
        if not credentials.exists():
            logger.debug(f'Named profile credentials file "{credentials}" does not exist')
            return False
        config = ConfigParser()
        config.read(credentials)
        return name in config.sections()

    def session(self, organization: Optional[str] = None) -> Session:
        """
        Return a session that uses the organization ID named profile credentials (if it exists).
        """
        organization_id = self.organization_id(organization=organization)
        profile = organization_id if self.profile_exists(organization_id) else None
        if profile:
            logger.debug(f'Using named profile "{profile}"')
        return Session(profile_name=profile)
