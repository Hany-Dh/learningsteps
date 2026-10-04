import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request, Depends
from repositories.postgres_repository import PostgresDB
from services.entry_service import EntryService
from models.entry import Entry, EntryCreate


router = APIRouter()


# TODO: Add authentication middleware
# TODO: Add request validation middleware
# TODO: Add rate limiting middleware
# TODO: Add API versioning
# TODO: Add response caching


async def get_entry_service() -> AsyncGenerator[EntryService, None]:
    async with PostgresDB() as db:
        yield EntryService(db)


async def parse_request_body(request: Request) -> dict:
    """
    Accept both JSON and plain-text request bodies.

    JSON example:
    {
        "work": "Learned Kubernetes",
        "struggle": "Networking was difficult",
        "intention": "Practice AKS tomorrow"
    }

    Plain text example:
    Learned Kubernetes today.
    """

    content_type = request.headers.get("content-type", "").lower()

    # -------------------------
    # JSON request
    # -------------------------
    if "application/json" in content_type:
        try:
            data = await request.json()

            if not isinstance(data, dict):
                raise HTTPException(
                    status_code=400,
                    detail="JSON body must be an object."
                )

            return data

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON body."
            )

    # -------------------------
    # Plain text request
    # -------------------------
    if "text/plain" in content_type:
        body = await request.body()

        text = body.decode("utf-8").strip()

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Text body cannot be empty."
            )

        # A plain-text entry is stored in the "work" field.
        return {
            "work": text
        }

    # -------------------------
    # Unsupported content type
    # -------------------------
    raise HTTPException(
        status_code=415,
        detail="Unsupported Content-Type. Use application/json or text/plain."
    )


@router.post(
    "/entries",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "work": {"type": "string"},
                            "struggle": {"type": "string"},
                            "intention": {"type": "string"}
                        }
                    }
                },
                "text/plain": {
                    "schema": {
                        "type": "string",
                        "example": "I learned how AKS connects to Azure Container Registry today."
                    }
                }
            }
        }
    }
)
async def create_entry(
    request: Request,
    entry_service: EntryService = Depends(get_entry_service)
):
    """Create a new journal entry using JSON or plain text."""

    try:
        data = await parse_request_body(request)

        # JSON format
        entry_data = EntryCreate(**data)

        entry = Entry(
            work=entry_data.work,
            struggle=entry_data.struggle,
            intention=entry_data.intention
        )

        created_entry = await entry_service.create_entry(
            entry.model_dump()
        )

        return {
            "detail": "Entry created successfully",
            "entry": created_entry
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating entry: {str(e)}"
        )


@router.get("/entries")
async def get_all_entries(
    entry_service: EntryService = Depends(get_entry_service)
):
    """Get all journal entries."""

    result = await entry_service.get_all_entries()

    return {
        "entries": result,
        "count": len(result)
    }


@router.get("/entries/{entry_id}")
async def get_entry(
    entry_id: str,
    entry_service: EntryService = Depends(get_entry_service)
):
    """Get a single journal entry by ID."""

    entry = await entry_service.get_entry(entry_id)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Entry not found"
        )

    return entry


@router.patch(
    "/entries/{entry_id}",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "example": {
                            "work": "Updated learning text"
                        }
                    }
                },
                "text/plain": {
                    "schema": {
                        "type": "string",
                        "example": "I learned how Kubernetes services work."
                    }
                }
            }
        }
    }
)
async def update_entry(
    entry_id: str,
    request: Request,
    entry_service: EntryService = Depends(get_entry_service)
):
    """Update a journal entry using JSON or plain text."""

    try:
        entry_update = await parse_request_body(request)

        result = await entry_service.update_entry(
            entry_id,
            entry_update
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Entry not found"
            )

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error updating entry: {str(e)}"
        )


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    entry_service: EntryService = Depends(get_entry_service)
):
    """Delete a specific journal entry."""

    existing_entry = await entry_service.get_entry(entry_id)

    if not existing_entry:
        raise HTTPException(
            status_code=404,
            detail="Entry not found"
        )

    await entry_service.delete_entry(entry_id)

    return {
        "detail": "Entry deleted successfully"
    }


@router.delete("/entries")
async def delete_all_entries(
    entry_service: EntryService = Depends(get_entry_service)
):
    """Delete all journal entries."""

    await entry_service.delete_all_entries()

    return {
        "detail": "All entries deleted"
    }
