Connectors
==========
In the following we provide the reference for all currently available connectors.

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

Google Sheets
~~~~~~~~~~~~~
.. autoclass:: stormware.google.sheets.Spreadsheet
