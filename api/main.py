from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from routers.journal_router import router as journal_router
from prometheus_fastapi_instrumentator import Instrumentator
import logging

load_dotenv()

# TODO: Setup basic console logging
# Hint: Use logging.basicConfig() with level=logging.INFO
# Steps:
# 1. Configure logging with basicConfig()
# 2. Set level to logging.INFO
# 3. Add console handler
# 4. Test by adding a log message when the app starts

app = FastAPI(title="LearningSteps API", description="A simple learning journal API for tracking daily work, struggles, and intentions")
app.include_router(journal_router)

Instrumentator().instrument(app).expose(app)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
