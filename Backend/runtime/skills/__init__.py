from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .base import BaseSkill


def _load_skill_package(*, module_suffix: str, package_folder: str):
	module_name = f"{__name__}.{module_suffix}"
	if module_name in sys.modules:
		return sys.modules[module_name]

	package_dir = Path(__file__).resolve().parent / package_folder
	init_file = package_dir / "__init__.py"
	spec = importlib.util.spec_from_file_location(
		module_name,
		init_file,
		submodule_search_locations=[str(package_dir)],
	)
	if spec is None or spec.loader is None:
		raise ImportError(f"Cannot load skill package from {package_dir}")

	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


CCBGetHandlerSkill = _load_skill_package(
	module_suffix="skill_ccb_get_handler",
	package_folder="skill-ccb-get-handler",
).CCBGetHandlerSkill
DirectChatSkill = _load_skill_package(
	module_suffix="skill_direct_chat",
	package_folder="skill-direct-chat",
).DirectChatSkill
SendEmailSkill = _load_skill_package(
	module_suffix="skill_send_email",
	package_folder="skill-send-email",
).SendEmailSkill

__all__ = ["BaseSkill", "CCBGetHandlerSkill", "DirectChatSkill", "SendEmailSkill"]
