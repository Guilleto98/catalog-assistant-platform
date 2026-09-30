"""Bounded context and cache limits for the domain-scope guardrail."""


class ScopePolicy:
    MAX_LATEST_MESSAGE_CHARACTERS = 2_000
    MAX_RECENT_MESSAGE_CHARACTERS = 500
    MAX_RECENT_MESSAGES = 4
    MAX_TRACKED_INVOCATIONS = 2_048
