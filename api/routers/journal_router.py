kimport logging
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


def parse_text_entry(raw: str) -> dict:
    """
    Parse text/plain input.

    Supports two formats:

    1. Structured text:
       work: Studied FastAPI
       struggle: Understanding async/await
       intention: Practice PostgreSQL

    2. Normal text:
       Studied FastAPI and built my first API endpoint.

       Normal text is stored as the 'work' field.
    """

    raw = raw.strip()

    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Text body cannot be empty."
        )

    # Check whether this is key:value format
    lines = raw.splitlines()

    if any(":" in line for line in lines):
        data = {}

        for line in lines:
            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            key = key.strip().lower()
            value = value.strip()

            if key in {"work", "struggle", "intention"}:
                data[key] = value

        # If at least one valid field was found,
        # treat it as structured text.
        if data:
            return data

    # Otherwise treat the entire text as the work field
    return {
        "work": raw,
        "struggle": "",
        "intention": ""
    }


def get_request_body_schema():
    """
    OpenAPI schema for both JSON and plain-text requests.
    """

    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/EntryCreate"
                },
                "example": {
                    "work": "Studied FastAPI and built my first API endpoint",
                    "struggle": "Understanding async/await",
                    "intention": "Practice PostgreSQL"
                }
            },
            "text/plain": {
                "schema": {
                    "type": "string"
                },
                "example": "Today I studied FastAPI and built my first API endpoint."
            }
        }
    }


@router.post(
    "/entries",
    openapi_extra={
        "requestBody": get_request_body_schema()
    }
)
async def create_entry(
    request: Request,
    entry_service: EntryService = Depends(get_entry_service)
):
    """
    Create a new journal entry.

    Supports:
    - application/json
    - text/plain
    """

    try:
        content_type = request.headers.get(
            "content-type",
            ""
        ).lower()

        # -----------------------------
        # JSON
        # -----------------------------
        if "application/json" in content_type:

            try:
                body = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON body."
                )

            if not isinstance(body, dict):
                raise HTTPException(
                    status_code=400,
                    detail="JSON body must be an object."
                )

            entry_data = EntryCreate(**body)

        # -----------------------------
        # Plain text
        # -----------------------------
        elif "text/plain" in content_type:

            raw = (await request.body()).decode("utf-8")

            parsed = parse_text_entry(raw)

            # Add empty values for fields that are
            # not supplied in structured text.
            parsed.setdefault("work", "")
            parsed.setdefault("struggle", "")
            parsed.setdefault("intention", "")

            entry_data = EntryCreate(**parsed)

        # -----------------------------
        # Unsupported content type
        # -----------------------------
        else:

            raise HTTPException(
                status_code=415,
                detail=(
                    "Unsupported Content-Type. "
                    "Use application/json or text/plain."
                )
            )

        # -----------------------------
        # Create Entry
        # -----------------------------

        entry = Entry(
            work=entry_data.work,
            struggle=entry_data.struggle,
            intention=entry_data.intention
        )

        # Store entry in database
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


# -----------------------------------------
# GET ALL ENTRIES
# -----------------------------------------

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


# -----------------------------------------
# GET SINGLE ENTRY
# -----------------------------------------

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


# -----------------------------------------
# UPDATE ENTRY
# -----------------------------------------

@router.patch(
    "/entries/{entry_id}",
    openapi_extra={
        "requestBody": get_request_body_schema()
    }
)
async def update_entry(
    request: Request,
    entry_id: str,
    entry_service: EntryService = Depends(get_entry_service)
):
    """
    Update a journal entry.

    Supports:
    - application/json
    - text/plain
    """

    try:

        content_type = request.headers.get(
            "content-type",
            ""
        ).lower()

        # -----------------------------
        # JSON
        # -----------------------------
        if "application/json" in content_type:

            try:
                entry_update = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON body."
                )

            if not isinstance(entry_update, dict):
                raise HTTPException(
                    status_code=400,
                    detail="JSON body must be an object."
                )

        # -----------------------------
        # Plain text
        # -----------------------------
        elif "text/plain" in content_type:

            raw = (await request.body()).decode("utf-8")

            entry_update = parse_text_entry(raw)

        # -----------------------------
        # Unsupported
        # -----------------------------
        else:

            raise HTTPException(
                status_code=415,
                detail=(
                    "Unsupported Content-Type. "
                    "Use application/json or text/plain."
                )
            )

        # Update database
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


# -----------------------------------------
# DELETE SINGLE ENTRY
# -----------------------------------------

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


# -----------------------------------------
# DELETE ALL ENTRIES
# -----------------------------------------

@router.delete("/entries")
async def delete_all_entries(
    entry_service: EntryService = Depends(get_entry_service)
):
    """Delete all journal entries."""

    await entry_service.delete_all_entries()

    return {
        "detail": "All entries deleted"
    }
