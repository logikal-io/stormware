Authentication
==============
External APIs typically require the caller to present a set of authentication credentials. In the
case of cloud infrastructure providers (Google Cloud Platform and Amazon Web Services in
particular) Stormware uses locally available credentials that are generated and also used by cloud
CLI tools.

.. note::

    You must install the ``google`` extra when using the Google Cloud Platform authentication
    mechanism.

.. note::

    You must install the ``amazon`` extra when using the Amazon Web Services authentication
    mechanism.

Google Cloud Platform
---------------------
The default authentication mechanism (implemented in :class:`~stormware.google.auth.GCPAuth`) first
looks for a set of credentials in the
``$XDG_CONFIG_HOME/gcloud/credentials/{organization_id}.json`` file, where ``organization_id`` is
derived from the provided ``organization`` value by replacing dots with dashes. If the organization
credentials file does not exist, we use the application default credentials.

.. note::

    We recommend using the `gcpl script
    <https://github.com/logikal-io/scripts/blob/main/bin/gcpl>`_ for generating organization
    credentials. Note that you need to add the ``-s stormware`` option if you are using Google
    connectors that are not related to the Google Cloud Platform (for example, the
    :ref:`connectors:Google Sheets` connector).

A default organization and project can be set under the ``tool.stormware`` section of a project's
``pyproject.toml`` file as follows:

.. code-block:: toml

    [tool.stormware]
    organization = 'example.com'
    project = 'my-project'

Amazon Web Services
-------------------
The authentication logic is implemented in :class:`~stormware.amazon.auth.AWSAuth` – we look for
the credentials of the ``organization_id`` named profile, which is derived the same way as it is
for the Google Cloud Platform authentication. If the credentials cannot be found for the named
profile then the ``boto3`` :ref:`credential location mechanism <boto3:guide_credentials>` is used.

.. note::

    We recommend using the `awsl script
    <https://github.com/logikal-io/scripts/blob/main/bin/awsl>`_ for generating named profile
    credentials.

Secret Store
------------
The credentials for most connectors are retrieved from a secret store, which has the following
abstract interface:

.. autoclass:: stormware.secrets.SecretStore
    :special-members: __getitem__

Stormware comes with two built-in secret store implementations for :ref:`Google Cloud Platform
<connectors:Google Secret Manager>` and :ref:`Amazon Web Services <connectors:AWS Secrets
Manager>`, and further secret stores can be easily added by simply inheriting and implementing the
:class:`~stormware.secrets.SecretStore` interface.

.. note::

    When no secret store is explicitly provided the connectors default to using the Google Cloud
    Secret Manager store when the ``google`` extra is installed and the AWS Secrets Manager store
    when the ``amazon`` extra is installed. If both extras are installed, the Google Cloud Secret
    Manager store takes precedence.

For further information regarding connector authentication please consult the documentation of the
specific :ref:`connector <connectors:Connectors>` that you intend to use.

Authentication Managers
-----------------------
.. autoclass:: stormware.google.auth.GCPAuth
.. autoclass:: stormware.amazon.auth.AWSAuth
