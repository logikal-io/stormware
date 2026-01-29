from pathlib import Path

from pytest import Config, Item, Session


def pytest_collection_modifyitems(
    session: Session,  # pylint: disable=unused-argument
    config: Config,
    items: list[Item],
) -> None:
    for item in items:
        relative_path = Path(item.fspath).relative_to(config.rootpath)
        if str(relative_path).startswith('tests/stormware/integration/'):
            item.add_marker('integration')
