from pydantic import BaseModel, Field


class CreateCardRequest(BaseModel):
    summary: str
    description: str | None = None
    project_id: str = Field(..., alias="projectId")

    class Config:
        populate_by_name = True


class UpdateEmailRequest(BaseModel):
    issue_id: str = Field(..., alias="issueId")
    new_email: str = Field(..., alias="newEmail")

    class Config:
        populate_by_name = True


class SetStateRequest(BaseModel):
    state_name: str = Field(..., alias="stateName")

    class Config:
        populate_by_name = True


class AddCommentRequest(BaseModel):
    text: str


class WebhookPayload(BaseModel):
    custom_field: str | None = Field(default=None, alias="customField")

    class Config:
        populate_by_name = True
        
class UpdateNameRequest(BaseModel):
    issue_id: str | None = Field(default=None, alias="issueId")
    email: str
    current_first_name: str | None = Field(default=None, alias="currentFirstName")
    current_last_name: str | None = Field(default=None, alias="currentLastName")
    new_first_name: str = Field(..., alias="newFirstName")
    new_last_name: str = Field(..., alias="newLastName")

    class Config:
        populate_by_name = True