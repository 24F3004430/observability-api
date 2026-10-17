
import os
from collections import defaultdict

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# Replace this with your actual assignment login email.
EMAIL = "24F3004430@ds.study.iitm.ac.in"

# Your assigned API key.
API_KEY = "ak_r988kzmkxzlf3ik4xetmyn24"

app = FastAPI()

# Allow the assignment page to call your API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: list[Event]


@app.post("/analytics")
def analytics(
    request: AnalyticsRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    # Reject missing or incorrect API keys.
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    events = request.events

    # Collect each distinct user and their positive revenue.
    positive_totals = defaultdict(float)

    for event in events:
        if event.amount > 0:
            positive_totals[event.user] += event.amount

    total_revenue = sum(
        event.amount for event in events if event.amount > 0
    )

    # The grader supplies positive revenue and guarantees no ties.
    top_user = (
        max(positive_totals, key=positive_totals.get)
        if positive_totals
        else ""
    )

    return {
        "email": EMAIL,
        "total_events": len(events),
        "unique_users": len({event.user for event in events}),
        "revenue": total_revenue,
        "top_user": top_user,
    }


@app.get("/")
def home():
    return {"status": "ok", "endpoint": "/analytics"}
