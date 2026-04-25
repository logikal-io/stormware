from datetime import datetime, timezone
from pathlib import Path

from pytest import raises

from stormware.google.gmail import Address, Gmail, Label, Message, Query


def test_labels(gmail: Gmail) -> None:
    test_label = Label(id='Label_8536780189888046773', name='Test Label')
    labels = gmail.labels()
    assert test_label in labels


def test_messages(gmail: Gmail) -> None:
    messages = gmail.messages(
        query=Query(
            sender='non-existent-sender@logikal.io',
            to='non-existent-to@logikal.io',
            subject='Non-Existent Subject',
            timestamp_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            timestamp_to=datetime(2025, 1, 15, tzinfo=timezone.utc),
        ),
    )
    assert messages == []


def test_message(gmail: Gmail, tmp_path: Path) -> None:
    messages = sorted(gmail.messages(
        query=Query(
            subject='Google Cloud Platform & APIs: Your invoice is available',
            timestamp_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            timestamp_to=datetime(2026, 1, 31, tzinfo=timezone.utc),
            attachment=True,
            labels=[Label(id='Label_8536780189888046773')],
        ),
    ))
    assert messages == [
        Message(id='19bfbd77159b6b61', thread_id='19bfbd77159b6b61'),
        Message(id='19bfbd818d21cdc5', thread_id='19bfbd818d21cdc5'),
    ]

    message = gmail.message(messages[0])
    assert message.id == '19bfbd77159b6b61'
    assert message.thread_id == '19bfbd77159b6b61'
    assert message.sender
    assert message.sender.display_name == 'Gergely Kalmár'
    assert message.to == [Address(email='test.user@logikal.io', display_name='Test User')]
    assert not message.cc
    assert message.subject
    assert 'Google Cloud Platform & APIs' in message.subject
    assert message.plain_text
    assert 'Google Cloud Platform & APIs monthly invoice' in message.plain_text
    assert message.html_text
    assert 'Google Cloud Platform &amp; APIs monthly invoice' in message.html_text
    assert message.timestamp == datetime(2026, 1, 26, 19, 45, 30, tzinfo=timezone.utc)
    assert message.attachments
    assert message.attachments[0].message_id == '19bfbd77159b6b61'
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
