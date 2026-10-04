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


def parse_text_entry(raw: str) -> dict:
    """Parses 'key: value' lines (one per line) into a dict."""
    data = {}
    for line in raw.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower()] = value.strip()
    return data


@router.post("/entries")
async def create_entry(request: Request, entry_service: EntryService = Depends(get_entry_service)):
    """Create a new journal entry. Accepts application/json or text/plain (key: value per line)."""
    try:
        content_type = request.headers.get("content-type", "")
        if "text/plain" in content_type:
            raw = (await request.body()).decode()
            parsed = parse_text_entry(raw)
            entry_data = EntryCreate(**parsed)
        else:
            body = await request.json()
            entry_data = EntryCreate(**body)

        # Create the full entry with auto-generated fields
        entry = Entry(
            work=entry_data.work,
            struggle=entry_data.struggle,
            intention=entry_data.intention
        )

        # Store the entry in the database
        created_entry = await entry_service.create_entry(entry.model_dump())

        # Return success response (FastAPI handles datetime serialization automatically)
        return {
            "detail": "Entry created successfully",
            "entry": created_entry
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating entry: {str(e)}")

# Implements GET /entries endpoint to list all journal entries
# Example response: [{"id": "123", "work": "...", "struggle": "...", "intention": "..."}]
@router.get("/entries")
async def get_all_entries(entry_service: EntryService = Depends(get_entry_service)):
    """Get all journal entries."""
    result = await entry_service.get_all_entries()
    return {"entries": result, "count": len(result)}

@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str, entry_service: EntryService = Depends(get_entry_service)):
    """Get a single journal entry by ID."""
    entry = await entry_service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry

@router.patch("/entries/{entry_id}")
async def update_entry(request: Request, entry_id: str, entry_service: EntryService = Depends(get_entry_service)):
    """Update a journal entry. Accepts application/json or text/plain (key: value per line)."""
    content_type = request.headers.get("content-type", "")
    if "text/plain" in content_type:
        raw = (await request.body()).decode()
        entry_update = parse_text_entry(raw)
    else:
        entry_update = await request.json()

    result = await entry_service.update_entry(entry_id, entry_update)
    if not result:

        raise HTTPException(status_code=404, detail="Entry not found")

    return result

@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, entry_service: EntryService = Depends(get_entry_service)):
    """Delete a specific journal entry."""
    existing_entry = await entry_service.get_entry(entry_id)
    if not existing_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await entry_service.delete_entry(entry_id)
    return {"detail": "Entry deleted successfully"}

@router.delete("/entries")
async def delete_all_entries(entry_service: EntryService = Depends(get_entry_service)):
    """Delete all journal entries"""
    await entry_service.delete_all_entries()
    return {"detail": "All entries deleted"}
