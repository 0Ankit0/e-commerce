import importlib
import logging
from typing import TYPE_CHECKING

from django.conf import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from common.tasks import LambdaTask
else:
    module_name, package = settings.LAMBDA_TASKS_BASE_HANDLER.rsplit(".", maxsplit=1)
    LambdaTask = getattr(importlib.import_module(module_name), package)


class ContentfulSync(LambdaTask):
    def __init__(self, name: str):
        super().__init__(name=name, source="backend.contentfulSync")

    def apply(self):
        super().apply({})
