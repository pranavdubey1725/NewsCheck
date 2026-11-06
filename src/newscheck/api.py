import traceback

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from newscheck.pipeline import Event, check_stream

app = FastAPI(title="newscheck")


class CheckRequest(BaseModel):
    text: str


@app.post("/check")
def check(req: CheckRequest) -> StreamingResponse:
    def events():
        try:
            for event in check_stream(req.text):
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception:
            traceback.print_exc()
            error = Event(stage="error", message="Something went wrong while checking this post. Please try again.")
            yield f"data: {error.model_dump_json()}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")