"""
Gmail API connector.
"""
# Documentation:
# - Google API Python Client Library: https://googleapis.github.io/google-api-python-client/
# - Gmail API: https://developers.google.com/gmail/api
import base64
import email
from dataclasses import dataclass
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth

logger = getLogger(__name__)


@dataclass(order=True, kw_only=True)
class Label:
    """
    Represents a label.
    """
    id: str
    name: str | None = None


@dataclass(order=True, kw_only=True)
class Attachment:
    """
    Represents an email message attachment.
    """
    id: str
    message_id: str
    filename: str
    mime_type: str | None


@dataclass(order=True, kw_only=True)
class Address:
    """
    Represents an email address.
    """
    email: str
    display_name: str | None = None


@dataclass(order=True, kw_only=True)
class Message:  # pylint: disable=too-many-instance-attributes
    """
    Represents an email message.
    """
    id: str
    thread_id: str | None = None
    sender: Address | None = None
    to: list[Address] | None = None
    cc: list[Address] | None = None
    subject: str | None = None
    plain_text: str | None = None
    html_text: str | None = None
    timestamp: datetime | None = None
    labels: list[Label] | None = None
    attachments: list[Attachment] | None = None

    @staticmethod
    def _decode_part_body_data(part: dict[str, dict[str, str]]) -> str:
        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

    def add_part(self, part: dict[str, Any]) -> None:
        mime_type = part.get('mimeType')
        if mime_type == 'text/plain':
            self.plain_text = self._decode_part_body_data(part)
        elif mime_type == 'text/html':
            self.html_text = self._decode_part_body_data(part)
        elif mime_type == 'multipart/alternative':
            for subpart in part['parts']:
                self.add_part(subpart)


@dataclass(kw_only=True)
class Query:  # pylint: disable=too-many-instance-attributes
    """
    Represents a Gmail `search query <https://support.google.com/mail/answer/7190?hl=en>`_.
    """
    text: str = ''
    sender: str | None = None
    to: str | None = None
    cc: str | None = None
    subject: str | None = None
    timestamp_from: datetime | None = None
    timestamp_to: datetime | None = None
    label: str | None = None
    labels: list[Label] | None = None
    attachment: bool | None = None

    def __str__(self) -> str:
        query: list[str] = [self.text] if self.text else []
        if self.sender:
            query.append(f'from:{self.sender}')
        if self.to:
            query.append(f'to:{self.to}')
        if self.cc:
            query.append(f'cc:{self.cc}')
        if self.subject:
            query.append(f'subject:({self.subject})')
        if self.timestamp_from:
            query.append(f'after:{int(self.timestamp_from.timestamp())}')
        if self.timestamp_to:
            query.append(f'before:{int(self.timestamp_to.timestamp())}')
        if self.label:
            query.append(f'label:({self.label})')
        if self.attachment:
            query.append('has:attachment')
        return ' '.join(query)


class Gmail(ClientManager[Any]):
    def __init__(
        self,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
    ):
        """
        Gmail connector.

        Must be used with a context manager.

        Args:
            organization: The organization to use.
            project: The project to use.
            auth: The Google Cloud Platform authentication manager to use. Note that the
                credentials must be authorized for the
                ``https://www.googleapis.com/auth/gmail.readonly`` scope.

        """
        super().__init__()
        self.auth = auth or GCPAuth(organization=organization, project=project)

    def create_client(self) -> Any:  # pragma: no cover
        return build(
            'gmail', 'v1',
            credentials=self.auth.credentials(), cache_discovery=False,
        )

    def labels(self, *, user_id: str = 'me') -> list[Label]:
        """
        Load labels.

        Args:
            user_id: The user ID to use.

        """
        response = self.client.users().labels().list(  # pylint: disable=no-member
            userId=user_id
        ).execute()
        return [Label(id=label['id'], name=label['name']) for label in response.get('labels', [])]

    def messages(self, query: Query, *, user_id: str = 'me') -> list[Message]:
        """
        Load messages that match a given query.

        Args:
            query: The query to use.
            user_id: The user ID to use.

        """
        logger.info(f'Loading messages of user "{user_id}"')
        query_str = str(query)
        logger.debug(f'Using query: {query_str}')
        messages: list[dict[str, str]] = []
        page = 0
        page_token = None
        while True:  # pylint: disable=while-used
            page += 1
            logger.debug(f'Loading page {page}')
            response = self.client.users().messages().list(  # pylint: disable=no-member
                q=query_str,
                userId=user_id,
                labelIds=[label.id for label in query.labels or []],
                includeSpamTrash=False,
                pageToken=page_token,
                fields='nextPageToken, messages(id, threadId)',
            ).execute()
            messages.extend(response.get('messages', []))
            if not (page_token := response.get('nextPageToken')):
                return [
                    Message(id=message['id'], thread_id=message.get('threadId'))
                    for message in messages
                ]

    @staticmethod
    def _parse_address(addresses: str) -> list[Address]:
        return [
            Address(email=field[1], display_name=field[0] or None)
            for field in email.utils.getaddresses([addresses])
        ]

    def message(self, message: Message, *, user_id: str = 'me') -> Message:
        """
        Load a specific message.
        """
        logger.info(f'Loading message "{message.id}" of user "{user_id}"')
        fields = ', '.join([
            'id', 'threadId', 'labelIds', 'internalDate',
            f'payload({', '.join([
                'partId', 'headers', 'mimeType', 'filename', 'body(data)',
                f'parts({', '.join([
                    'partId', 'mimeType', 'filename', 'body(data, attachmentId)',
                    'parts(partId, mimeType, filename, body(data))',
                ])})',
            ])})',
        ])
        response = self.client.users().messages().get(  # pylint: disable=no-member
            userId=user_id,
            id=message.id,
            format='full',
            fields=fields,
        ).execute()

        message = Message(
            id=response['id'],
            thread_id=response.get('threadId'),
            to=[],
            cc=[],
            timestamp=datetime.fromtimestamp(int(response['internalDate']) / 1000, timezone.utc),
            labels=[Label(id=label_id) for label_id in response.get('labelIds')],
            attachments=[],
        )

        # Process headers
        for header in response.get('payload', {}).get('headers', []):
            if header['name'].lower() == 'from':
                message.sender = self._parse_address(header['value'])[0]
            elif header['name'].lower() == 'to':
                message.to = self._parse_address(header['value'])
            elif header['name'].lower() == 'cc':
                message.cc = self._parse_address(header['value'])
            elif header['name'].lower() == 'subject':
                message.subject = header['value']

        # Process message parts
        for part in response.get('payload', {}).get('parts', []):
            if 'attachmentId' in part.get('body', {}):
                message.attachments.append(  # type: ignore[union-attr]
                    Attachment(
                        id=part['body']['attachmentId'],
                        message_id=response['id'],
                        filename=part['filename'],
                        mime_type=part.get('mimeType'),
                    )
                )
            else:
                message.add_part(part)

        return message

    def download_attachment(  # pylint: disable=too-many-arguments
        self,
        attachment: Attachment,
        *,
        dst: Path,
        filename: str | None = None,
        overwrite: bool | None = None,
        user_id: str = 'me',
    ) -> Path:
        """
        Download an attachment and return a path to it.

        Args:
            attachment: The attachment information object.
            dst: The destination folder to use.
            filename: The filename to use. Defaults to using the attachment filename.
            overwrite: Whether to overwrite existing files.
                Raises a :class:`FileExistsError` by default.
            user_id: The user ID to use.

        """
        dst_path = dst / (filename or attachment.filename)
        dst_full_path = dst_path.expanduser()
        if dst_full_path.exists():
            if overwrite is None:
                raise FileExistsError(f'Destination file "{dst_path}" already exists')
            if overwrite is False:
                logger.info(f'Skipping downloading existing file "{dst_path}"')
                return dst_path

        logger.info(
            f'Downloading attachment of message "{attachment.message_id}" of user "{user_id}" '
            f'to "{dst_path}"'
        )
        logger.debug(f'Attachment ID: {attachment.id}')
        response = self.client.users().messages().attachments().get(  # pylint: disable=no-member
            userId=user_id,
            messageId=attachment.message_id,
            id=attachment.id,
        ).execute()

        logger.info(f'Saving attachment to "{dst_path}"')
        dst.expanduser().mkdir(parents=True, exist_ok=True)
        dst_full_path.write_bytes(base64.urlsafe_b64decode(response['data']))
        return dst_path
