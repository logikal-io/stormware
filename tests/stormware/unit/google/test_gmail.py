import base64
from datetime import datetime, timezone
from pathlib import Path

from pytest import raises
from pytest_mock import MockerFixture

from stormware.google.gmail import Address, Attachment, Gmail, Label, Message, Query


def test_query() -> None:
    assert 'text from:sender to:to' in str(Query(
        text='text',
        sender='sender',
        to='to',
        cc='cc',
        subject='subject',
        timestamp_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        timestamp_to=datetime(2025, 3, 1, tzinfo=timezone.utc),
        label='label',
        labels=[Label(id='test_label')],
        attachment=True,
    ))


def test_labels(mocker: MockerFixture) -> None:
    client = mocker.patch('stormware.google.gmail.Gmail.create_client').return_value
    client.users.return_value.labels.return_value.list.return_value.execute.return_value = {
        'labels': [
            {'id': 'label_1', 'name': 'Label 1'},
            {'id': 'label_2', 'name': 'Label 2'},
        ],
    }
    with Gmail() as gmail:
        labels = sorted(gmail.labels())
        assert labels == [
            Label(id='label_1', name='Label 1'),
            Label(id='label_2', name='Label 2'),
        ]


def test_messages(mocker: MockerFixture) -> None:
    client = mocker.patch('stormware.google.gmail.Gmail.create_client').return_value
    client.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
        {'messages': [{'id': 'message_1', 'threadId': 'thread_1'}], 'nextPageToken': 'token'},
        {'messages': [{'id': 'message_2', 'threadId': 'thread_2'}]},
    ]
    with Gmail() as gmail:
        messages = sorted(gmail.messages(query=Query(text='query')))
        assert messages == [
            Message(id='message_1', thread_id='thread_1'),
            Message(id='message_2', thread_id='thread_2'),
        ]


def test_message(mocker: MockerFixture) -> None:
    plain_text = 'plain text'
    html_text = '<h1>HTML text</h1>'
    plain_text_data = base64.urlsafe_b64encode(plain_text.encode())
    html_text_data = base64.urlsafe_b64encode(html_text.encode())

    timestamp = datetime(2025, 2, 15, 10, 45, 35, tzinfo=timezone.utc)
    client = mocker.patch('stormware.google.gmail.Gmail.create_client').return_value
    client.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        'id': 'message_1',
        'threadId': 'thread_1',
        'labelIds': ['label_1', 'label_2'],
        'payload': {
            'headers': [
                {'name': 'From', 'value': '"Test From" <test-from@example.com>'},
                {'name': 'To', 'value': ', '.join([
                    '"Test To 1" <test-to-1@example.com>', '"Test To 2" <test-to-2@example.com>',
                ])},
                {'name': 'Cc', 'value': ', '.join([
                    '"Test Cc 1" <test-cc-1@example.com>', '"Test Cc 2" <test-cc-2@example.com>',
                ])},
                {'name': 'Subject', 'value': 'Message subject'},
            ],
            'parts': [
                {
                    'mimeType': 'application/pdf', 'filename': 'file.pdf',
                    'body': {'attachmentId': 'attachment_1'},
                },
                {
                    'mimeType': 'multipart/alternative',
                    'parts': [
                        {'mimeType': 'text/plain', 'body': {'data': plain_text_data}},
                        {'mimeType': 'text/html', 'body': {'data': html_text_data}},
                    ],
                },
            ],
        },
        'internalDate': timestamp.timestamp() * 1000,
    }
    with Gmail() as gmail:
        message = gmail.message(Message(id='message_1'))
        assert message == Message(
            id='message_1',
            thread_id='thread_1',
            sender=Address(email='test-from@example.com', display_name='Test From'),
            to=[
                Address(email='test-to-1@example.com', display_name='Test To 1'),
                Address(email='test-to-2@example.com', display_name='Test To 2'),
            ],
            cc=[
                Address(email='test-cc-1@example.com', display_name='Test Cc 1'),
                Address(email='test-cc-2@example.com', display_name='Test Cc 2'),
            ],
            subject='Message subject',
            plain_text=plain_text,
            html_text=html_text,
            timestamp=timestamp,
            labels=[Label(id='label_1'), Label(id='label_2')],
            attachments=[Attachment(
                id='attachment_1', message_id='message_1',
                filename='file.pdf', mime_type='application/pdf',
            )],
        )


def test_download_attachment(mocker: MockerFixture, tmp_path: Path) -> None:
    test_file = Path(__file__).parents[1] / 'data/test_file.txt'
    data = base64.urlsafe_b64encode(test_file.read_bytes())
    client = mocker.patch('stormware.google.gmail.Gmail.create_client').return_value
    attachments = client.users.return_value.messages.return_value.attachments.return_value
    attachments.get.return_value.execute.return_value = {'data': data}
    with Gmail() as gmail:
        attachment = Attachment(
            id='attachment_1', message_id='message_1',
            filename='test.txt', mime_type=None,
        )
        path = gmail.download_attachment(attachment, dst=tmp_path)
        assert path.read_text() == test_file.read_text()

        path = gmail.download_attachment(attachment, dst=tmp_path, overwrite=False)  # skip
        assert path.exists()

        with raises(FileExistsError):
            gmail.download_attachment(attachment, dst=tmp_path)
