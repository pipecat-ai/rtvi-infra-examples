import os
from modal import Secret, App, Image, web_endpoint
from fastapi import HTTPException
from typing import Dict

MAX_SESSION_TIME = 5 * 60  # 5 minutes


def download_models():
    # Download a cache the Silero model, to reduce cold start time
    import torch
    torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)


image = (
    Image
    .debian_slim(python_version="3.12")
    .pip_install(
        "pydantic==2.8.2",
        "pipecat-ai[daily,openai,cartesia,silero]==0.0.39",
        "httpx",
        "requests",
        "loguru",
        "websockets")
    .run_function(download_models)
)

app = App("pipecat-example")


@app.function(image=image,
              secrets=[Secret.from_name("rtvi-example-secrets")],
              keep_warm=0,  # Do not reuse instances as the pipeline needs to be restarted
              timeout=MAX_SESSION_TIME,
              container_idle_timeout=2,
              max_inputs=1,  # Do not reuse instances as the pipeline needs to be restarted
              retries=0)
async def run_bot(room_url: str, token: str, config: Dict):
    # Bot function (Pipecat + RTVI)

    import aiohttp
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.processors.frameworks.rtvi import (
        RTVIConfig,
        RTVIProcessor,
        RTVISetup)
    from pipecat.frames.frames import EndFrame
    from pipecat.transports.services.daily import DailyParams, DailyTransport
    from pipecat.vad.silero import SileroVADAnalyzer

    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            room_url,
            token,
            "Realtime AI",
            DailyParams(
                audio_out_enabled=True,
                transcription_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer()
            ))

        rtai = RTVIProcessor(
            transport=transport,
            setup=RTVISetup(config=RTVIConfig(**config)),
            llm_api_key=os.getenv("OPENAI_API_KEY", ""),
            tts_api_key=os.getenv("CARTESIA_API_KEY", ""))

        runner = PipelineRunner()

        pipeline = Pipeline([transport.input(), rtai])

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                send_initial_empty_metrics=False,
            ))

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            transport.capture_participant_transcription(participant["id"])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await task.queue_frame(EndFrame())

        @transport.event_handler("on_call_state_updated")
        async def on_call_state_updated(transport, state):
            if state == "left":
                await task.queue_frame(EndFrame())

        await runner.run(task)


@app.function(image=image,
              secrets=[Secret.from_name("rtvi-example-secrets")],
              keep_warm=1)
@web_endpoint(method="POST")
def server(config: Dict):
    # Web endpoint for launching a bot

    from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomObject, DailyRoomProperties, DailyRoomParams

    DAILY_API_URL = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
    DAILY_DOMAIN = os.getenv("DAILY_DOMAIN", "https://rtvi.daily.co")
    DAILY_API_KEY = os.getenv("DAILY_API_KEY", "")

    if not config:
        raise Exception("Missing RTVI configuration object for bot")

    # Note: Ideally validate the config object here, before spawing the bot

    # Create a Daily rest helper
    daily_rest_helper = DailyRESTHelper(DAILY_API_KEY, DAILY_API_URL)

    # Check if we should use an existing room, or create a new one
    debug_room = os.getenv("USE_DEBUG_ROOM", None)
    if debug_room:
        # Check debug room URL exists, and grab it's properties
        try:
            room: DailyRoomObject = daily_rest_helper.get_room_from_url(
                f"{DAILY_DOMAIN}/{debug_room}")
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
        # Spawn the agent VM
        run_bot.spawn(room.url, token, config)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start subprocess: {e}")

    # Grab a token for the user to join with
    user_token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    return {
        "room_name": room.name,
        "room_url": room.url,
        "token": user_token
    }
