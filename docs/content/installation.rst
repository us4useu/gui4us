============
Installation
============

GUI4US is available in the PyPI repository, which means you can install
the latest release by running the command:

::

    pip install gui4us


.. warning::

   If you encounter the following problem while launching gui4us on **Windows**:

   ``from PyQt5.QtWidgets import QApplication ... ImportError: DLL load failed: The specified module could not be found.``

   It means you need to execute the following additional commands in Conda:

   ``pip uninstall PyQt5 PyQt5-Qt5 PyQt5_sip``

   ``conda install pyqt``
