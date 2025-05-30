"""Simple tracer utility for LangSmith integration."""

import logging
import os
import traceback
from collections.abc import Callable
from typing import TypeVar

from langsmith import Client
from langsmith.run_helpers import traceable

from backend.app.core.config_manager import settings

logger = logging.getLogger(__name__)

# Type variable for function return type
T = TypeVar('T')

# Variable to store client reference
client = None


def get_client():
    """Get or create a LangSmith client.

    This function can be called multiple times and will return the existing client
    or create a new one if needed.
    """
    global client

    # If client already exists, return it
    if client is not None:
        return client

    # Otherwise, try to create a new client
    try:
        if settings.LANGCHAIN_API_KEY:
            # Log all environment variables that might affect LangSmith
            logger.info(f'LANGCHAIN_API_KEY exists (length: {len(settings.LANGCHAIN_API_KEY)})')
            logger.info(f'LANGCHAIN_ENDPOINT: {settings.LANGCHAIN_ENDPOINT}')
            logger.info(f'LANGCHAIN_PROJECT: {settings.LANGCHAIN_PROJECT}')
            logger.info(f'LANGCHAIN_TRACING_V2: {settings.LANGCHAIN_TRACING_V2}')

            # Set environment variables to ensure LangSmith internal checks pass
            if settings.LANGCHAIN_TRACING_V2:
                os.environ['LANGCHAIN_TRACING_V2'] = 'true'
            os.environ['LANGCHAIN_API_KEY'] = settings.LANGCHAIN_API_KEY
            os.environ['LANGCHAIN_PROJECT'] = settings.LANGCHAIN_PROJECT
            if settings.LANGCHAIN_ENDPOINT:
                os.environ['LANGCHAIN_ENDPOINT'] = settings.LANGCHAIN_ENDPOINT

            # Log system environment variables for diagnostic purposes
            langchain_env_vars = {k: v for k, v in os.environ.items() if k.startswith('LANGCHAIN_')}
            logger.info(f'System environment variables: {langchain_env_vars}')

            new_client = Client(
                api_key=settings.LANGCHAIN_API_KEY,
                api_url=settings.LANGCHAIN_ENDPOINT or None,
            )
            logger.info(f'LangSmith client initialized for project: {settings.LANGCHAIN_PROJECT}')
            client = new_client
            return client
        else:
            logger.warning('LangSmith client not initialized (no API key provided)')
            return None
    except Exception as e:
        logger.exception(f'Failed to initialize LangSmith client: {e}')
        return None


# Initialize client (but it can be refreshed later)
client = get_client()


def trace_rag(func: Callable[..., T]) -> Callable[..., T]:
    # Simple tracer for RAG functions.

    def wrapper(*args, **kwargs) -> T:
        # Add debug context
        func_name = func.__name__
        logger.debug(f'trace_rag called for function: {func_name}')

        # Check if tracing is enabled and refresh client if needed
        if not settings.LANGCHAIN_TRACING_V2:
            logger.debug(f'Tracing disabled for {func_name} - LANGCHAIN_TRACING_V2 is False')
            return func(*args, **kwargs)

        # Get or refresh client
        current_client = get_client()
        if not current_client:
            logger.warning(f'Cannot trace {func_name}: no LangSmith client available')
            return func(*args, **kwargs)

        # Log tracing info for debugging
        logger.info(f'Tracing {func_name} with LangSmith project: {settings.LANGCHAIN_PROJECT}')

        try:
            # Create a traceable version of the function
            logger.debug(f'Creating traceable version of {func_name} with client: {current_client} and project: {settings.LANGCHAIN_PROJECT}')
            traced_func = traceable(
                run_type='chain',
                name=func_name,
                tags=['rag'],
                client=current_client,
                project_name=settings.LANGCHAIN_PROJECT,
            )(func)

            # Log that we're about to execute the function
            logger.debug(f'Executing traced function: {func_name}')

            # Execute the function and get result
            result = traced_func(*args, **kwargs)

            # Log successful tracing
            logger.info(f'Successfully traced {func_name} call (function returned normally)')
            return result
        except Exception as e:
            # Log the exception for easier debugging
            logger.exception(f'Error during tracing of {func_name}: {e}')
            logger.error(f'Traceback: {traceback.format_exc()}')

            # Fall back to untraced function
            logger.warning(f'Falling back to untraced execution of {func_name}')
            return func(*args, **kwargs)

    return wrapper
