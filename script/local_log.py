from loguru import logger
from rich.logging import RichHandler

logger.configure(handlers=[{'sink': RichHandler()}])

logger.info('The logger is initialized.')
