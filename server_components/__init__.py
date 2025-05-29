"""
This file makes the 'server_components' directory a Python package.
It can also be used to control what is exported when using 'from server_components import *'
or to perform package-level initializations. For now, it's kept simple.
"""
# You can selectively import modules here if you want to control the package's public API, e.g.:
# from . import config
# from . import common
# from . import api_general_routes
# ... and so on.
# For now, direct imports from ws_server.py (e.g., from server_components import api_admin_routes) will work.

# Initialize a package-level logger if desired, though individual module loggers are common.
import logging
logger = logging.getLogger(__name__)
logger.info("server_components package initialized.")
