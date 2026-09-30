"""Validated request models for authenticated platform routes."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .policies import RequestLimits


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        min_length=RequestLimits.EMAIL_MIN_CHARACTERS,
        max_length=RequestLimits.EMAIL_MAX_CHARACTERS,
    )
    password: str = Field(
        min_length=1,
        max_length=RequestLimits.PASSWORD_MAX_CHARACTERS,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_message_id: str = Field(alias="clientMessageId")
    text: str | None = Field(default=None, max_length=RequestLimits.MAX_MESSAGE_CHARACTERS)
    attachment_ids: list[str] = Field(
        default_factory=list,
        alias="attachmentIds",
        max_length=RequestLimits.MAX_ATTACHMENTS_PER_MESSAGE,
    )

    @field_validator("client_message_id")
    @classmethod
    def normalize_client_message_id(cls, value: str) -> str:
        return str(UUID(value))

    @field_validator("text")
    @classmethod
    def normalize_meaningful_text(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None

    @model_validator(mode="after")
    def validate_message_content(self) -> "SendMessageRequest":
        if not self.text and not self.attachment_ids:
            raise ValueError("Se requiere texto o adjuntos.")
        if len(set(self.attachment_ids)) != len(self.attachment_ids):
            raise ValueError("Los adjuntos no pueden repetirse.")
        return self
