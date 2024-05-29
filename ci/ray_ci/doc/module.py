import importlib
import inspect
from types import ModuleType
from typing import List, Dict

from ci.ray_ci.doc.api import API, AnnotationType, CodeType


class Module:
    """
    Module class represents the top level module to walk through and find annotated
    APIs.
    """

    def __init__(self, module: str):
        self._module = importlib.import_module(module)
        self._visited = set()
        self._apis = []

    def walk(self) -> None:
        self._walk(self._module)

    def get_apis(self) -> List[API]:
        self.walk()
        return self._apis

    def _walk(self, module: ModuleType) -> None:
        """
        Depth-first search through the module and its children to find annotated classes
        and functions.
        """
        if module in self._visited:
            return
        self._visited.add(module.__hash__)
        aliases = self._get_aliases()

        if not self._is_valid_child(module):
            return

        for child in dir(module):
            attribute = getattr(module, child)

            if inspect.ismodule(attribute):
                self._walk(attribute)
            if inspect.isclass(attribute):
                if self._is_api(attribute):
                    self._apis.append(
                        API(
                            name=self._fullname(attribute, aliases),
                            annotation_type=self._get_annotation_type(attribute),
                            code_type=CodeType.CLASS,
                        )
                    )
                self._walk(attribute)
            if inspect.isfunction(attribute):
                if self._is_api(attribute):
                    self._apis.append(
                        API(
                            name=self._fullname(attribute, aliases),
                            annotation_type=self._get_annotation_type(attribute),
                            code_type=CodeType.FUNCTION,
                        )
                    )

        return

    def _fullname(self, attribute: ModuleType, aliases: Dict[str, str]) -> str:
        module = attribute.__module__
        name = attribute.__qualname__
        fullname = f"{module}.{name}"
        if fullname in aliases:
            return aliases[fullname]
        if module in aliases:
            return f"{aliases[module]}.{name}"

        return fullname

    def _is_valid_child(self, module: ModuleType) -> bool:
        """
        This module is a valid child of the top level module if it is the top level
        module itself, or its module name starts with the top level module name.
        """
        module = inspect.getmodule(module)
        if not hasattr(module, "__name__"):
            return False
        return module.__name__.startswith(self._module.__name__)

    def _is_api(self, module: ModuleType) -> bool:
        return self._is_valid_child(module) and hasattr(module, "_annotated")

    def _get_annotation_type(self, module: ModuleType) -> AnnotationType:
        return AnnotationType(module._annotated_type.value)

    def _get_aliases(self) -> Dict[str, str]:
        """
        In the __init__ file of the root module, it might define aliases for the module.
        If an alias exists, we should use the alias instead of the module name.
        """
        aliases = {}
        for child in dir(self._module):
            attribute = getattr(self._module, child)
            if not inspect.isclass(attribute) and not inspect.isfunction(attribute):
                # only classes and functions can be aliased
                continue
            fullname = f"{attribute.__module__}.{attribute.__qualname__}"
            alias = f"{self._module.__name__}.{attribute.__qualname__}"
            aliases[fullname] = alias

        return aliases
