import base64
from datetime import datetime, timezone
from pathlib import Path

from pytest import mark, raises
from pytest_mock import MockerFixture

from stormware.google.gmail import Attachment, Gmail, Label, Message, Query


def test_query() -> None:
    assert 'text from:sender to:to' in str(Query(
        'text',
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


@mark.skip(reason="these email messages are specific to Gergely's account")
def test_integration(gmail: Gmail, tmp_path: Path) -> None:
    messages = sorted(gmail.messages(
        query=Query(
            sender='payments-noreply@google.com',
            subject='Google Cloud Platform & APIs: Your invoice is available',
            timestamp_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            timestamp_to=datetime(2025, 3, 1, tzinfo=timezone.utc),
            attachment=True,
            labels=[Label(id='CATEGORY_UPDATES')],
        ),
    ))
    assert messages == [
        Message(id='194254ea8cff4383', thread_id='194254ea8cff4383'),
        Message(id='194c40cae1b67443', thread_id='194c40cae1b67443'),
    ]

    message = gmail.message(messages[0])
    assert message.id == '194254ea8cff4383'
    assert message.thread_id == '194254ea8cff4383'
    assert message.timestamp == datetime(2025, 1, 2, 4, 38, 18, tzinfo=timezone.utc)
    assert message.attachments
    assert message.attachments[0].message_id == '194254ea8cff4383'
    assert message.attachments[0].mime_type == 'application/pdf'

    filename = f'invoice_google_cloud_{message.timestamp.strftime('%Y%m%d')}.pdf'
    attachment = gmail.download_attachment(
        attachment=message.attachments[0],
        dst=tmp_path,
        filename=filename,
    )
    assert attachment.exists()

    # Try downloading again
    with raises(FileExistsError):
        gmail.download_attachment(
            attachment=message.attachments[0],
            dst=tmp_path,
            filename=filename,
        )


def test_messages(gmail: Gmail, mocker: MockerFixture) -> None:
    client = mocker.patch('stormware.google.gmail.Gmail.create_client').return_value
    client.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
        {'messages': [{'id': 'message_1', 'threadId': 'thread_1'}], 'nextPageToken': 'token'},
        {'messages': [{'id': 'message_2', 'threadId': 'thread_2'}]},
    ]
    with Gmail() as gmail:
        messages = sorted(gmail.messages(query=Query('query')))
        assert messages == [
            Message(id='message_1', thread_id='thread_1'),
            Message(id='message_2', thread_id='thread_2'),
        ]


def test_message(gmail: Gmail, mocker: MockerFixture) -> None:
    timestamp = datetime(2025, 2, 15, 10, 45, 35, tzinfo=timezone.utc)
    client = mocker.patch('stormware.google.gmail.Gmail.create_client').return_value
    client.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        'id': 'message_1',
        'threadId': 'thread_1',
        'labelIds': ['label_1', 'label_2'],
        'payload': {'parts': [{
            'mimeType': 'application/pdf', 'filename': 'file.pdf',
            'body': {'attachmentId': 'attachment_1'},
        }]},
        'internalDate': timestamp.timestamp() * 1000,
    }
    with Gmail() as gmail:
        message = gmail.message(Message(id='message_1'))
        assert message == Message(
            id='message_1', thread_id='thread_1',
            timestamp=timestamp,
            labels=[Label(id='label_1'), Label(id='label_2')],
            attachments=[Attachment(
                id='attachment_1', message_id='message_1',
                filename='file.pdf', mime_type='application/pdf',
            )],
        )


def test_download_attachment(gmail: Gmail, mocker: MockerFixture, tmp_path: Path) -> None:
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

        with raises(FileExistsError):
            gmail.download_attachment(attachment, dst=tmp_path)
