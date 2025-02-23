Connectors
==========
In the following we provide the reference for all currently available connectors.

Amazon
------
You can install the Amazon connectors through the ``amazon`` extra:

.. code-block:: shell

    pip install stormware[amazon]

.. note::

    All Amazon connectors use the AWS credentials that are obtained through the authentication
    mechanism described in the :ref:`auth:Amazon Web Services` section of the authentication
    documentation.

AWS Secrets Manager
~~~~~~~~~~~~~~~~~~~
.. autoclass:: stormware.amazon.secrets.SecretsManager
    :special-members: __getitem__

Facebook
--------
You can install the Facebook connectors through the ``facebook`` extra:

.. code-block:: shell

    pip install stormware[facebook]

.. autoclass:: stormware.facebook.FacebookAds

Google
------
You can install the Google connectors through the ``google`` extra:

.. code-block:: shell

    pip install stormware[google]

.. note::

    All Google connectors use the Google credentials that are obtained through the authentication
    mechanism described in the :ref:`auth:Google Cloud Platform` section of the authentication
    documentation.

Google BigQuery
~~~~~~~~~~~~~~~
.. autoclass:: stormware.google.bigquery.BigQuery

Google Drive
~~~~~~~~~~~~~
.. autoclass:: stormware.google.drive.DrivePath
    :show-inheritance:
    :no-inherited-members:

.. autoclass:: stormware.google.drive.Drive

Google Secret Manager
~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: stormware.google.secrets.SecretManager
    :special-members: __getitem__

Google Sheets
~~~~~~~~~~~~~
.. autoclass:: stormware.google.sheets.Spreadsheet
