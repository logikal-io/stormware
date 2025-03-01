Stormware
=========
API connectors for data analysis and task automation.

Getting Started
---------------
You can find the project documentation under `docs.logikal.io/stormware/
<https://docs.logikal.io/stormware/>`_.

Authentication
--------------
Note that you will need to execute the following steps to be able to run the test suite locally:

1. Download the ``Stormware`` OAuth client ID file from the `Cloud Console
   <https://console.cloud.google.com/apis/credentials>`_ in the ``Stormware`` project and save it
   at ``~/.config/gcloud/client_id_files``
2. Authenticate using `gcpl
   <https://github.com/logikal-io/ansible-public-playbooks/blob/main/roles/gcp/files/bin/gcpl>`_ as
   follows::

     gcpl -c logikal-io-stormware -e <your_email>@logikal.io -p stormware-logikal-io \
       -s stormware -i ~/.config/gcloud/client_id_files/stormware-logikal-io.json
