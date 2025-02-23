from itertools import product
from logging import getLogger
from pathlib import Path
from time import sleep

from pytest import mark, param, raises
from pytest_mock import MockerFixture

from stormware.google.drive import Drive, DrivePath

logger = getLogger(__name__)

# Local paths
TEST_FOLDER_PATH = Path(__file__).parent / 'Stormware Test - upload'
TEST_FILE_PATH = TEST_FOLDER_PATH / 'Stormware Test - upload.txt'

# Google Drive paths
SHARED_DRIVE_ROOT = DrivePath('//Software Engineering')
USER_DRIVE_ROOT = DrivePath('/')
DUPLICATE_FOLDER = SHARED_DRIVE_ROOT / 'Stormware Tests/Duplicate Folder'
DUPLICATE_FILE = SHARED_DRIVE_ROOT / 'Stormware Tests/Duplicate File.txt'


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


def test_drive_not_found(drive: Drive) -> None:
    with raises(RuntimeError, match='not found'):
        drive.exists(DrivePath('//Non-Existent Test Drive'))


def test_drive_not_unique(mocker: MockerFixture) -> None:
    client = mocker.patch('stormware.google.drive.Drive.create_client').return_value
    client.drives.return_value.list.return_value.execute.return_value = {
        'drives': [{'id': 1}, {'id': 2}],
    }
    with raises(RuntimeError, match='not unique'):
        with Drive() as drive:
            drive.exists(DrivePath('//Non-Unique Test Drive'))


@mark.parametrize('drive_path', [
    param(DUPLICATE_FILE, id='file'),
    param(DUPLICATE_FOLDER, id='folder'),
])
def test_exists_duplicate(drive: Drive, drive_path: DrivePath) -> None:
    with raises(RuntimeError, match='not unique'):
        assert drive.exists(drive_path)


@mark.parametrize('drive_root', [
    param(SHARED_DRIVE_ROOT, id='shared_drive'),
    param(USER_DRIVE_ROOT, id='user_drive'),
])
@mark.parametrize('subpath', [
    param('Stormware Tests/Test mkdir folder', id='folder'),
    param('Stormware Tests/Test mkdir subfolder/Subfolder', id='subfolder'),
])
def test_mkdir(drive: Drive, drive_root: DrivePath, subpath: str) -> None:
    if not drive_root.drive:
        subpath = subpath.replace('Stormware Tests/', 'Stormware Test - ')
    drive_path = drive_root / subpath

    # Prepare clean destinations
    drive.remove(drive_path, missing_ok=True)
    assert not drive.exists(drive_path)
    sleep(5)  # wait for consistency

    # Create folder
    path = drive.mkdir(drive_path)
    assert drive.exists(path)
    sleep(5)  # wait for consistency

    # Try creating the same folder again (should not create a duplicate)
    path = drive.mkdir(drive_path)
    assert drive.exists(path)
    sleep(5)  # wait for consistency

    # Move folder to trash
    drive.remove(path, use_trash=False)
    assert not drive.exists(path)

    # Delete parent folder of subfolder
    if 'subfolder' in subpath:
        drive.remove(path.parent, use_trash=False)


@mark.parametrize('drive_path', [
    param(DUPLICATE_FOLDER, id='folder'),
    param(DUPLICATE_FOLDER / 'Subfolder', id='subfolder'),
])
def test_mkdir_duplicate_error(drive: Drive, drive_path: DrivePath) -> None:
    with raises(RuntimeError, match='not unique'):
        drive.mkdir(drive_path)


def test_remove_non_existent(drive: Drive) -> None:
    non_existent_path = SHARED_DRIVE_ROOT / 'Stormware Tests/Test remove non-existent'
    with raises(FileNotFoundError, match='No such file or folder'):
        drive.remove(non_existent_path)
    drive.remove(non_existent_path, missing_ok=True)  # no error


def test_remove_errors(drive: Drive) -> None:
    with raises(ValueError, match='cannot be used together'):
        path = SHARED_DRIVE_ROOT / 'Stormware Tests/Test remove errors'
        drive.remove(path, use_trash=True, in_trash=True)


@mark.parametrize('drive_path', [
    param(SHARED_DRIVE_ROOT, id='shared_drive_root'),
    param(USER_DRIVE_ROOT, id='user_drive_root'),
])
def test_remove_invalid_path_errors(drive: Drive, drive_path: DrivePath) -> None:
    with raises(ValueError, match='Invalid path'):
        drive.remove(drive_path)


@mark.parametrize('drive_root', [
    param(SHARED_DRIVE_ROOT, id='shared_drive'),
    param(USER_DRIVE_ROOT, id='user_drive'),
])
def test_upload(drive: Drive, drive_root: DrivePath) -> None:
    src_types = {'file': TEST_FILE_PATH, 'folder': TEST_FOLDER_PATH}
    dst_paths = ['Stormware Tests/Test upload' if drive_root.drive else 'Stormware Test - upload']
    if not drive_root.drive:
        dst_paths += ['']  # execute against root on the user's drive but not on the shared drive
    for src_type, dst_path in product(src_types.keys(), dst_paths):
        src = src_types[src_type]
        dst = drive_root
        if dst_path:
            dst /= f'{dst_path} {src_type}'

        logger.info(f'Testing upload of "{src}" to "{dst}"')

        # Prepare clean destinations
        drive.remove(dst / src.name, missing_ok=True)
        assert not drive.exists(dst / src.name)
        sleep(5)  # wait for consistency

        # Upload source path
        path = drive.upload(src=src, dst=dst)
        sleep(5)  # wait for consistency

        # Check uploaded files
        if src.is_file():
            assert drive.exists(path)
        elif src.is_dir():
            for src_path, _, filenames in src.walk():
                dst_folder = dst / src.name / src_path.relative_to(src)
                assert drive.exists(dst_folder)
                for filename in filenames:
                    assert drive.exists(dst_folder / filename)

        # Upload again with overwrite
        drive.upload(src=src, dst=dst, overwrite=True)
        sleep(5)  # wait for consistency

        # Upload again without overwrite
        with raises(RuntimeError, match='already exists'):
            drive.upload(src=src, dst=dst, overwrite=False)

        # Clean up user drive
        if not dst.drive:
            drive.remove(path, use_trash=False)
            if dst_path:
                drive.remove(path.parent, use_trash=False)


def test_upload_non_existent(drive: Drive) -> None:
    with raises(ValueError, match='does not exist'):
        drive.upload(src=Path('non-existent source path'), dst=SHARED_DRIVE_ROOT)


def test_upload_invalid_source_path(drive: Drive, mocker: MockerFixture) -> None:
    with raises(ValueError, match='Invalid source path'):
        src = mocker.Mock()
        src.exists.return_value = True
        src.is_file.return_value = False
        src.is_dir.return_value = False
        drive.upload(src=src, dst=SHARED_DRIVE_ROOT)
