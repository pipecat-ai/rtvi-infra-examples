# RTVI Local Infrastructure Example

Example for testing your clients in development, containing everything you need to connect a bot to your RTVI client. It can also be used as a starting point for building your own realtime AI voice and video workflows on your deployment target of choice.

For low traffic use-cases, where running as processes is adequete, this example is cloud-deploy ready and Dockerfiles are included.

This project includes two Python files:

🏃‍♀️ `runner.py` HTTP service for starting new realtime sessions by spawning new bot agents at the specified transport URL.

🤖 `bot.py` The chatbot agent, leveraging Pipecat and the library's RTVI framework implementation.


The example bot included in this project does not require any GPU-enabled platform to run, instead opting for AI services that are available via http / websockets (no local models.) You can, of course, configure your pipeline to use on-premises models if you prefer.

**Note: The term 'local' in this project name refers to the ability to spawn agents as Python processes on your local computer instead of containerizing and deploying them to the cloud. Please note, however, that the bot services still require an active internet connection to function.**


## Quickstart

#### Install the development dependencies:

```bash
python -m venv venv
source venv/bin/activate # or OS equivalent
pip install -r bot/requirements.txt
pip install -r runner/requirements.txt
```

**Please note: the Daily SDK (`daily-python`) required by the bot files is not currently supported on Windows. The required dependencies will currently fail to install unless you use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).**

#### Create environment files for both apps:

```bash
cp runner/env.example runner/.env
cp bot/env.example bot/.env
```

Enter the necessary (required) API keys for both applications.


#### Start the bot runner server:

```bash
cd runner
python bot_runner.py --host localhost --reload
```

#### Send a POST request to the runner URL:

```bash
curl --location --request POST 'http://localhost:7860' \
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

Note: the first time you run this method, it may take a few minutes to download the necessary dependencies.


#### Configure your RTVI client

You can pass the URL of your bot runner to your RTVI client like so:

```typescript
import { VoiceClient } from "realtime-ai";

const voiceClient = new VoiceClient({
  baseUrl: "http://localhost:7860", // as an example
  enableMic: true,
  config: {...},
});
```

## Deployment

This repo doesn't make any hosting platform assumptions and simply launches the bot as a subprocess of a single machine / VM. Great for smaller use-cases where you do not need to run more than 5-10 concurrent bots.

You can read more about the deployment pattern adopted in this example [here](https://docs.pipecat.ai/deployment/pattern).


## HTTP service / bot runner

In order for your client to start a new realtime session with your bot, you should create an HTTP service that expects a JSON formatted pipeline configuration object. When a new request is sent, the runner will spawn a new bot agent, passing the necessary connectivity and configuration details.


### Configuration options

#### Project `.env`

The runner looks for the following environment variables in order to spawn your agent:

`HOST_WHITELIST`

A comma-delimited list of allowed hosts. This will prevent outside requests from spawning a bot.

_Note: this is for illustrative purposes as a rudimentary example of securing your runner. Malicious actors can easily spoof the request domain. In production use-cases, you should protect your runner service with the necessary measures to prevent unwanted activity._

`USE_DEBUG_ROOM`

By default, a runner will create a new room for the realtime session with each request. In local development, you may prefer to work with the same room each time (to avoid exceeding transport service room limits, etc.). Pass the name / url of the room here, in the case of Daily this would look like `USE_DEBUG_ROOM=https://yourdomain.daily.co`.

`DAILY_API_KEY`

This example is configured to use [Daily](https://www.daily.co) as the default realtime media transport. You can obtain your developer key for your domain by visiting your [Daily dashboard](https://dashboard.daily.co).


## Bot file

The example bot file included in this project uses the [Pipecat](https://www.pipecat.ai) RTVI framework implementation to run a realtime voice session. It uses the following services:

- [Daily](www.daily.co) for realtime media transport (WebRTC)
- Daily for real-time user transcription (Deepgram)
- [OpenAI](https://openai.com/) for LLM inference. Note: you can use whichever OpenAI compatible service you prefer, such as Groq.
- [Cartesia](https://cartesia.ai/) for text-to-speech.


#### Project `.env`

Your bot file requires the necessary service API keys to run inference based on the configuration of your RTVI pipeline or request services. Out of the box, we implement both Cartesia and [Groq](https://groq.com/).

You can change which LLM service your bot uses by passing an optional `llm_base_url` to the RTVIProcessor constructor method.

You do not need to pass your Daily API key to this app as an access is sent from the bot runner, allowing it to connect to the room. If working with the defaults, your .env file should look like this:

```bash
CARTESIA_API_KEY=your-key-here
OPENAI_API_KEY=your-groq-key-here
```

## Building docker containers

Both the `runner` and `bot` apps contain example Dockerfiles that you can use to build and deploy your applications. 

We recommend deploying these apps independently, but please note that doing so will require you to configure your runner accordingly to your chosen hosting platform. An example of how to do this with Fly.io can be found [here](https://docs.pipecat.ai/deployment/fly).


You can build your apps like this:

```bash
docker build -t registry.fly.io/rtvi-runner:latest .

docker build -t registry.fly.io/rtvi-bot:latest . --platform linux/amd64
```

_Note: The bot application requires PyTorch / CUDA to leverage Silero VAD. For this reason, please target the correct platform during build. Torch significantly increases the size of the resulting image; we have found that Torch CPU does not work as well with Silero (even though no GPU is required for this demo.)_