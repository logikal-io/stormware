import logging


def pytest_configure() -> None:
    logging.getLogger('botocore').setLevel(logging.INFO)  # DEBUG is too verbose
    logging.getLogger('requests_oauthlib').setLevel(logging.INFO)  # DEBUG contains sensitive data
