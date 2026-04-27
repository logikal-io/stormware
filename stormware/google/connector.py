class Connector:  # pylint: disable=too-few-public-methods
    """
    Base class for all connectors.
    """
    SCOPES: list[str] = []

    @staticmethod
    def all_scopes() -> list[str]:
        scopes = []
        for connector in Connector.__subclasses__():
            scopes.extend(connector.SCOPES)
        return scopes
