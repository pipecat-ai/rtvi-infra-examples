# RTVI Modal.com Example

[Modal](htts://www.modal.com) provides a great way to quickly both CPU and GPU-enabled bots, ideal if your want to use your own on-premises models.

Modal provides several ways to go about this; using their Python SDK with decorators, or invovking functions directly. You can also push Docker images directly and launch machines via their API.

Modal also provides a way to create a web endpoint within your projects which is a handy way to abbreviate the typical Pipecat [deployment pattern](https://docs.pipecat.ai/deployment/pattern).

This examples explores a simple implementation in a single `app.py` file and only scratches the surface of the platforms capabilities. As a next step, you may want to explore concurrency, reducing cold start timers and other API methods useful for production scale!


**Note: This example does not secure your Modal deployments. Be sure to implement adequete authentication when shipping to production**

## Getting started

#### Install the Modal Python SDK

`pip install modal`

#### Login to Modal, if you haven't already

`python -m modal setup`

#### Setup app secrets

After setup, you will be prompted to enter your app secrets. This demo assumes this set is called `rtvi-example-secrets`, but you can change this to anything you like. Please ensure you set the following secrets:

```
CARTESIA_API_KEY

DAILY_API_KEY

DAILY_DOMAIN

OPENAI_API_KEY
```

**Note: you can do this programmatically if you prefer, see docs [here](https://modal.com/docs/guide/secrets#programmatic-creation-of-secrets).


You can optionally set `USE_DEBUG_ROOM` to specific Daily room name.

By default, a this example will create a new room for the realtime session with each request. In local development, you may prefer to work with the same room each time (to avoid exceeding transport service room limits, etc.). Pass the name of the room here, e.g., `USE_DEBUG_ROOM=test`. In the case of Daily, this should be just the room name, not the full URL.

At time of writing, you may need to use the more recent image builder to avoid Python dependency conflicts (Pydantic, FastAPI):

`export MODAL_IMAGE_BUILDER_VERSION=2024.04`


#### Launch and test your app:

`modal serve app.py`

This will build and deploy an app and provide you with a URL to connect to your bot in the terminal.

#### Give it a quick test

```bash
curl --location --request POST 'YOUR MODAL URL HERE' \
--header 'Content-Type: application/json' \
--data '{
    "config": {
        "llm": {
            "model": "llama3-70b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant named Chatbot. Briefly say hello!"
                }
            ]
        },
        "tts": {
            "voice": "79a125e8-cd45-4c13-8a67-188112f4dd22"
        }
    }
}'
```

All being well, you should see the output of the app in the terminal running `modal serve`.


#### Configure your RTVI client

You can pass the URL of your bot runner to your RTVI client like so:

```typescript
import { VoiceClient } from "realtime-ai";

const voiceClient = new VoiceClient({
  baseUrl: "https://YOUR-MODAL-APP-URL.modal.run"
  enableMic: true,
  config: {...},
});
```

#### Deploy your app

Your app is currently running in 'ephemeral' mode, meaning it will close once you exit the terminal process. To deploy it, simply run:

`python modal deploy`

## Services this example uses

- [Daily](www.daily.co) for realtime media transport (WebRTC)
- Daily for real-time user transcription (Deepgram)
- [OpenAI](https://openai.com/) for LLM inference. Note: you can use whichever OpenAI compatible service you prefer, such as Groq.
- [Cartesia](https://cartesia.ai/) for text-to-speech.