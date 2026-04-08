from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .base import BaseSkill
from .direct_chat import DirectChatSkill


def _load_ccb_get_handler_skill():
	module_name = f"{__name__}.skill_ccb_get_handler"
	if module_name in sys.modules:
		return sys.modules[module_name]

	package_dir = Path(__file__).resolve().parent / "skill-ccb-get-handler"
	init_file = package_dir / "__init__.py"
	spec = importlib.util.spec_from_file_location(
		module_name,
		init_file,
		submodule_search_locations=[str(package_dir)],
	)
	if spec is None or spec.loader is None:
		raise ImportError(f"Cannot load CCB skill package from {package_dir}")

	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


CCBGetHandlerSkill = _load_ccb_get_handler_skill().CCBGetHandlerSkill

__all__ = ["BaseSkill", "CCBGetHandlerSkill", "DirectChatSkill"]
