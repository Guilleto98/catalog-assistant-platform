from solvo_client_agent.agent import INSTRUCTION, root_agent
from solvo_client_agent.scope.callback import DomainScopeCallback
from google.adk.models.lite_llm import LiteLlm


def test_root_agent_has_complete_catalog_tools():
    assert root_agent.name == "solvo_client_root_agent"
    assert isinstance(root_agent.model, LiteLlm)
    assert root_agent.model.model == "openai/gpt-6-luna"
    assert [tool.__name__ for tool in root_agent.tools] == [
        "search_articles",
        "get_article",
        "compare_articles",
        "find_similar_articles",
        "get_technical_sheet",
        "get_filterable_fields",
        "get_request_draft",
        "update_request_draft",
        "save_filter",
        "list_saved_filters",
        "get_saved_filter",
        "execute_saved_filter",
        "delete_saved_filter",
    ]
    assert root_agent.sub_agents == []
    assert isinstance(root_agent.before_model_callback, DomainScopeCallback)
    assert "Solvo" not in INSTRUCTION
    assert "asistente generalista" in INSTRUCTION
