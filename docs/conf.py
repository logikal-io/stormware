import sys
from importlib.metadata import version as pkg_version

extensions = [
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]
intersphinx_mapping = {
    'python': (f'https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}', None),
    'pandas': (f'https://pandas.pydata.org/pandas-docs/version/{pkg_version("pandas")}', None),
    'boto3': (f'https://boto3.amazonaws.com/v1/documentation/api/{pkg_version("boto3")}/', None),
    'google.auth': (
        f'https://googleapis.dev/python/google-auth/{pkg_version("google-auth")}/', None,
    ),
}
