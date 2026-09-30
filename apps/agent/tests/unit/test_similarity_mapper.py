from datetime import datetime, timezone

from solvo_client_agent.domain.models import (
    ArticleRequestDraft,
    DraftField,
    DraftFieldStatus,
    DraftStatus,
    UserSource,
)
from solvo_client_agent.services import DraftSimilarityMapper


def field(path, value, status, *, required=False):
    return DraftField(
        field=path,
        raw_value=str(value),
        normalized_value=value,
        status=status,
        required=required,
        source=UserSource(),
    )


def draft(fields):
    now = datetime.now(timezone.utc)
    return ArticleRequestDraft(
        id="draft-1",
        conversation_id="conversation-1",
        source_attachment_ids=[],
        status=DraftStatus.READY,
        fields=fields,
        created_at=now,
        updated_at=now,
    )


METADATA = [
    {
        "path": "producto_destino.mercado",
        "type": "string",
        "allowedValues": ["CHINA", "BRASIL"],
        "usedForSimilarity": True,
        "canBeRequired": True,
    },
    {
        "path": "producto_destino.pais_destino",
        "type": "string",
        "allowedValues": ["CHINA", "BRASIL"],
        "usedForSimilarity": False,
        "canBeRequired": True,
    },
]


def test_mapper_uses_confirmed_and_corrected_and_maps_required_separately():
    mapped = DraftSimilarityMapper().map(
        draft([
            field("producto_destino.mercado", "CHINA", DraftFieldStatus.CONFIRMED, required=True),
            field("producto_destino.pais_destino", "CHINA", DraftFieldStatus.CORRECTED, required=True),
        ]),
        METADATA,
    )
    assert mapped.features == {"producto_destino.mercado": "CHINA"}
    assert mapped.required == {
        "producto_destino.mercado": "CHINA",
        "producto_destino.pais_destino": "CHINA",
    }
    assert mapped.used_fields[0].destinations == ["features", "required"]
    assert mapped.used_fields[1].destinations == ["required"]


def test_mapper_excludes_unconfirmed_and_invalid_values_by_default():
    mapped = DraftSimilarityMapper().map(
        draft([
            field("producto_destino.mercado", "CHINA", DraftFieldStatus.PROPOSED, required=True),
            field("producto_destino.mercado", "MARTE", DraftFieldStatus.CONFIRMED),
            field("producto_destino.mercado", "BRASIL", DraftFieldStatus.REJECTED),
        ]),
        METADATA,
    )
    assert mapped.features == {}
    assert mapped.required == {}
    assert [item.reason for item in mapped.ignored_fields] == [
        "status_proposed_not_active",
        "value_no_longer_valid",
        "status_rejected_not_active",
    ]


def test_explicit_proposed_data_is_optional_only():
    mapped = DraftSimilarityMapper().map(
        draft([
            field("producto_destino.mercado", "CHINA", DraftFieldStatus.PROPOSED, required=True),
        ]),
        METADATA,
        include_proposed=True,
    )
    assert mapped.features == {"producto_destino.mercado": "CHINA"}
    assert mapped.required == {}
