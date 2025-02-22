import logging
from django.core.management.base import BaseCommand
import traceback

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Tests exception logging in Django with deeper stack traces"

    def simple_error(self, e):
        """Extracts the exception name, HTTP status code (if applicable), filename, and line number."""
        tb = traceback.extract_tb(e.__traceback__)[0]  # Get last traceback entry
        error_msg = f"{type(e).__name__} in {tb.filename} at line {tb.lineno}"

        return error_msg

    def recursive_function(self, depth=3):
        """Recursively calls itself to create a deeper stack trace"""
        if depth == 0:
            raise ValueError("Intentional error at max recursion depth!")
        return self.recursive_function(depth - 1)

    def wrapper_function(self):
        """Wrapper function to add another layer to the stack"""
        return self.recursive_function()

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Running exception logging test..."))

        try:
            self.wrapper_function()  # Indirectly calls the recursive function
        except ValueError as e:
            logger.error("Caught a ValueError with logger.error")
            logger.exception("Caught a ValueError with logger.exception")
            logger.error(self.simple_error(e))  # Custom error message

        self.stdout.write(self.style.SUCCESS("Logging test completed. Check logs."))
