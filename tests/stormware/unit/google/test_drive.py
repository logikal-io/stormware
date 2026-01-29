from pytest import raises
from pytest_mock import MockerFixture

from stormware.google.drive import Drive, DrivePath


def test_drive_path() -> None:
    # Check drive
    assert not DrivePath('/').drive
    assert not DrivePath('/folder').drive
    assert DrivePath('//Drive').drive == 'Drive'
    assert DrivePath('//Drive/folder').drive == 'Drive'

    # Check division
    assert DrivePath('//Drive') / 'folder' == DrivePath('//Drive/folder')
    assert '//Drive' / DrivePath('/folder') == DrivePath('//Drive/folder')
    assert DrivePath('//Drive', 'folder') == DrivePath('//Drive/folder')

    # Check parent
    assert DrivePath('//Drive').parent == DrivePath('//Drive')
    assert DrivePath('//Drive/folder').parent == DrivePath('//Drive')
    assert DrivePath('//Drive/folder/subfolder').parent == DrivePath('//Drive/folder')

    # Check string representation
    assert str(DrivePath('/')) == '/'
    assert str(DrivePath('/folder')) == '/folder'
    assert str(DrivePath('/folder/')) == '/folder'
    assert str(DrivePath('//Drive')) == '//Drive/'
    assert str(DrivePath('//Drive/')) == '//Drive/'
    assert str(DrivePath('//Drive/folder')) == '//Drive/folder'
    assert str(DrivePath('//Drive/folder/')) == '//Drive/folder'

    # Check as_uri
    assert DrivePath('//Drive').as_uri() == 'gdrive://Drive/'
    assert DrivePath('//Drive/folder').as_uri() == 'gdrive://Drive/folder'


def test_drive_path_errors() -> None:
    with raises(ValueError):
        DrivePath()  # no path provided
    with raises(ValueError):
        DrivePath('invalid')  # path does not start with '/'
    with raises(ValueError):
        DrivePath('//')  # no shared drive name provided


def test_log_info() -> None:
    # pylint: disable=protected-access
    assert 'folder' in Drive._log_info('Test', folders=True)
    assert 'file' in Drive._log_info('Test', folders=False)
    assert 'in trash' in Drive._log_info('Test', in_trash=True)
    assert 'not in trash' in Drive._log_info('Test', in_trash=False)


def test_drive_not_unique(mocker: MockerFixture) -> None:
    client = mocker.patch('stormware.google.drive.Drive.create_client').return_value
    client.drives.return_value.list.return_value.execute.return_value = {
        'drives': [{'id': 1}, {'id': 2}],
    }
    with raises(RuntimeError, match='not unique'):
        with Drive() as drive:
            drive.exists(DrivePath('//Non-Unique Test Drive'))
