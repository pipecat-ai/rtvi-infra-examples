import os
import argparse
import subprocess
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, \
    DailyRoomObject, DailyRoomProperties, DailyRoomParams
from pipecat.processors.frameworks.rtvi import RTVIConfig

from dotenv import load_dotenv

load_dotenv(override=True)


# ------------ Fast API Config ------------ #

MAX_SESSION_TIME = 15 * 60  # 15 minutes

DAILY_API_URL = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
DAILY_API_KEY = os.getenv("DAILY_API_KEY", "")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------ Helper methods ------------ #


def escape_bash_arg(s):
    return "'" + s.replace("'", "'\\''") + "'"


def check_host_whitelist(request: Request):
    host_whitelist = os.getenv("HOST_WHITELIST", "")
    request_host_url = request.headers.get("host")

    if not host_whitelist:
        return True

    # Split host whitelist by comma
    allowed_hosts = host_whitelist.split(",")

    # Return True if no whitelist exists are specified
    if len(allowed_hosts) < 1:
        return True

    # Check for apex and www variants
    if any(domain in allowed_hosts for domain in [request_host_url, f"www.{request_host_url}"]):
        return True

    return False


# ------------ Fast API Routes ------------ #

@app.middleware("http")
async def allowed_hosts_middleware(request: Request, call_next):
    # Middle that optionally checks for hosts in a whitelist
    if not check_host_whitelist(request):
        raise HTTPException(status_code=403, detail="Host access denied")
    response = await call_next(request)
    return response


@app.post("/")
async def index(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        # Is this a webhook creation request?
        if "test" in data:
            return JSONResponse({"test": True})

        if "config" not in data:
            raise Exception("Missing RTVI configuration object for bot")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Missing configuration or malformed configuration object")

    try:
        bot_config = RTVIConfig(**data["config"])
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to parse bot configuration")

    # Create a Daily rest helper
    daily_rest_helper = DailyRESTHelper(DAILY_API_KEY, DAILY_API_URL)

    # Check if we should use an existing room, or create a new one
    debug_room = os.getenv("USE_DEBUG_ROOM", None)
    if debug_room:
        # Check debug room URL exists, and grab it's properties
        try:
            room: DailyRoomObject = daily_rest_helper.get_room_from_url(debug_room)
        except Exception:
            raise HTTPException(
                status_code=500, detail=f"Room not found: {debug_room}")
    else:
        # Create a new room
        try:
            params = DailyRoomParams(
                properties=DailyRoomProperties()
            )
            room: DailyRoomObject = daily_rest_helper.create_room(params=params)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{e}")

    # Give the agent a token to join the session
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token for room: {room.name}")

    # Launch a new VM as shell process (not recommended for production use)
    try:
        bot_file_path = Path("../bot").resolve()
        subprocess.Popen(
            [f"python3 -m bot -u {room.url} -t {token} -c {escape_bash_arg(bot_config.model_dump_json())}"],
            shell=True,
            bufsize=1,
            cwd=bot_file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start subprocess: {e}")

    # Grab a token for the user to join with
    user_token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    return JSONResponse({
        "room_name": room.name,
        "room_url": room.url,
        "token": user_token,
        "bot_config": bot_config.model_dump_json()
    })


# ------------ Main ------------ #

if __name__ == "__main__":
    # Check environment variables
    required_env_vars = ['DAILY_API_KEY']
    for env_var in required_env_vars:
        if env_var not in os.environ:
            raise Exception(f"Missing environment variable: {env_var}.")

    import uvicorn

    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "7860"))

    parser = argparse.ArgumentParser(
        description="RTVI Bot Runner")
    parser.add_argument("--host", type=str,
                        default=default_host, help="Host address")
    parser.add_argument("--port", type=int,
                        default=default_port, help="Port number")
    parser.add_argument("--reload", action="store_true",
                        help="Reload code on change")

    config = parser.parse_args()

    uvicorn.run(
        "bot_runner:app",
        host=config.host,
        port=config.port,
        reload=config.reload
    )
