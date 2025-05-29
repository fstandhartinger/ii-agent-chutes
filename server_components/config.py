"""
Manages global application configuration, primarily command-line arguments.
"""
import argparse
import logging

logger = logging.getLogger(__name__)

class AppConfig:
    """
    Singleton-like class to hold application configuration, primarily command-line arguments.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance.args = None
        return cls._instance

    def set_args(self, args: argparse.Namespace):
        """
        Sets the command-line arguments. This should be called once at startup.
        """
        if self.args is not None:
            logger.warning("Application arguments are being re-set. This is unusual.")
        self.args = args
        logger.info(f"Application arguments set: {args}")

    def get_args(self) -> Optional[argparse.Namespace]:
        """
        Retrieves the stored command-line arguments.
        """
        if self.args is None:
            logger.error("Application arguments accessed before being set. This may lead to errors.")
            # Potentially raise an error or return a default mock Namespace
            # For now, returning None and logging an error.
        return self.args

# Global instance of AppConfig
app_config = AppConfig()
