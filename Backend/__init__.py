__all__ = ["EmailSender", "LLMProvider", "SearchProvider"]


def __getattr__(name: str):
	if name == "EmailSender":
		from .integrations.email_sender import EmailSender

		return EmailSender
	if name == "LLMProvider":
		from .integrations.llm_provider import LLMProvider

		return LLMProvider
	if name == "SearchProvider":
		from .integrations.search_provider import SearchProvider

		return SearchProvider
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
