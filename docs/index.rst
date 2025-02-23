.. Documentation structure
.. toctree::
    :caption: Documentation
    :hidden:

    self
    auth
    connectors
    development
    license

.. toctree::
    :caption: External Links
    :hidden:

    Release Notes <https://github.com/logikal-io/stormware/releases>
    Issue Tracker <https://github.com/logikal-io/stormware/issues>
    Source Code <https://github.com/logikal-io/stormware>

Getting Started
===============
Stormware provides a unified interface to various external APIs via simple but powerful
:ref:`connectors <connectors:Connectors>`. It makes data engineering and data science work fast,
efficient and enjoyable.

Using the Connectors
--------------------
Let's say we need to load the results from our latest Facebook campaign into a Google Sheets
spreadsheet. We install Stormware with the appropriate connectors from `pypi
<https://pypi.org/project/stormware/>`_:

.. code-block:: shell

    pip install stormware[google,facebook]

We go through the authentication configuration steps for :ref:`Google <auth:Google Cloud Platform>`
and :ref:`Facebook <connectors:Facebook>`, and when done, we load the data into a data frame using
the Facebook Ads connector:

.. jupyter-execute::

    from stormware.facebook import FacebookAds

    facebook = FacebookAds(account_name='Logikal')
    report = facebook.report(
        metrics=['spend', 'impressions', 'clicks'],
        dimensions=['campaign_name'],
        parameters={
            'level': 'campaign',
            'time_range': {'since': '2023-01-01', 'until': '2023-01-07'},
        },
    )[['campaign_name', 'spend', 'impressions', 'clicks']]

.. jupyter-execute::

    report.head()

Finally, we push the data into the desired spreadsheet:

.. jupyter-execute::

    from stormware.google.sheets import Spreadsheet

    with Spreadsheet(key='1VV0cBAVeFTA5WUXYLvwmgZJtv-vV-q2uYr40lDAH3HA') as sheet:
        sheet.set_sheet(name='Facebook Campaign', data=report)

Of course, if we wanted to push the data into Google BigQuery as well, it would be equally easy:

.. jupyter-execute::

    from stormware.google.bigquery import BigQuery

    with BigQuery() as bigquery:
        bigquery.set_table(name='test.facebook_campaign', data=report)

That's it! Connectors are designed to be composable (for example, they will often return a
:class:`pandas.DataFrame` or expect one as an input), which makes common tasks much easier to
solve. Additionally, this approach also makes further analysis work with tools like `MindLab
<https://docs.logikal.io/mindlab/latest/>`_ simple and effortless.
