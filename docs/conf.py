import importlib
import sys


def pkg_version(package_name: str) -> str:
    if package_name == 'google-auth':
        # See https://github.com/googleapis/google-auth-library-python/issues/1593
        return '2.47.0'
    return importlib.metadata.version(package_name)


def strip_patch(package: str) -> str:
    return '.'.join(pkg_version(package).split('.')[0:2])  # major.minor (excluding patch)


extensions = [
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]
intersphinx_mapping = {
    'python': (f'https://docs.python.org/{sys.version_info[0]}.{sys.version_info[1]}', None),
    'pandas': (f'https://pandas.pydata.org/pandas-docs/version/{strip_patch("pandas")}', None),
    'boto3': (f'https://boto3.amazonaws.com/v1/documentation/api/{pkg_version("boto3")}/', None),
    'google.auth': (
        f'https://googleapis.dev/python/google-auth/{pkg_version("google-auth")}/', None,
    ),
}
