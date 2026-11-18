"""HTTP endpoints and temporary local demonstration identities."""

from enum import StrEnum
from pathlib import Path
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, StringConstraints

from .storage import ContactStore


class Stage(StrEnum):
    saved = "saved"
    contacted = "contacted"
    following_up = "following_up"


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Topic = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    research_group: Name
    research_topic: Topic


class StageChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: Stage


class Contact(Draft):
    id: UUID
    stage: Stage


def new_sessions() -> dict[str, str]:
    """Issue fresh, process-local tokens for the two invented workspaces."""
    return {workspace: token_urlsafe(32) for workspace in ("cairn", "rill")}


def create_app(path: Path, sessions: dict[str, str]) -> FastAPI:
    store = ContactStore(path)
    identities = {token: workspace for workspace, token in sessions.items()}
    bearer = HTTPBearer(auto_error=False)
    app = FastAPI(title="Research Contact Book", docs_url=None, redoc_url=None)

    def authenticate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        workspace = identities.get(credentials.credentials) if credentials else None
        if workspace is None:
            raise HTTPException(401, "A demo session is required", headers={"WWW-Authenticate": "Bearer"})
        return workspace

    Workspace = Annotated[str, Depends(authenticate)]

    def require_contact(row):
        if row is None:
            raise HTTPException(404, "Contact not found")
        return row

    @app.get("/contacts", response_model=list[Contact])
    def list_contacts(workspace: Workspace):
        return store.list_contacts(workspace)

    @app.post("/contacts", status_code=status.HTTP_201_CREATED, response_model=Contact)
    def create_contact(draft: Draft, workspace: Workspace):
        return store.create(workspace, draft.name, draft.research_group, draft.research_topic)

    @app.get("/contacts/{contact_id}", response_model=Contact)
    def get_contact(contact_id: UUID, workspace: Workspace):
        return require_contact(store.find(workspace, str(contact_id)))

    @app.patch("/contacts/{contact_id}", response_model=Contact)
    def change_stage(contact_id: UUID, change: StageChange, workspace: Workspace):
        return require_contact(store.set_stage(workspace, str(contact_id), change.stage.value))

    return app
