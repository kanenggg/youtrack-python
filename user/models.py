from typing import Annotated
from pydantic import BaseModel, Field


class CreateCardRequest(BaseModel):
    summary: str
    description: str | None = None
    project_id: Annotated[str, Field(alias="projectId")]

    model_config = {"populate_by_name": True}


class UpdateEmailRequest(BaseModel):
    issue_id: Annotated[str, Field(alias="issueId")]
    new_email: Annotated[str, Field(alias="newEmail")]

    model_config = {"populate_by_name": True}


class SetStateRequest(BaseModel):
    state_name: Annotated[str, Field(alias="stateName")]

    model_config = {"populate_by_name": True}


class AddCommentRequest(BaseModel):
    text: str


class WebhookPayload(BaseModel):
    custom_field: Annotated[str | None, Field(alias="customField")] = None

    model_config = {"populate_by_name": True}


class UpdateNameRequest(BaseModel):
    issue_id: Annotated[str | None, Field(alias="issueId")] = None
    email: str
    current_first_name: Annotated[str | None, Field(alias="currentFirstName")] = None
    current_last_name: Annotated[str | None, Field(alias="currentLastName")] = None
    new_first_name: Annotated[str, Field(alias="newFirstName")]
    new_last_name: Annotated[str, Field(alias="newLastName")]

    model_config = {"populate_by_name": True}