# RTVI Backend / Infrastructure Examples

This repository contains example applications for launching and deploying real-time bots that you can connect to with your RTVI-enabled clients. All of them will provide you with a base URL that you can pass to the Voice Client constructor, like so ...

```typescript
import { VoiceClient } from "realtime-ai";

const voiceClient = new VoiceClient({
    baseUrl: "http://localhost:7860", // as an example
    enableMic: true,
    config: {...},
});
```

... and launch a bot that you can talk with.

Most of the examples use the [Pipecat](www.pipecat.ai) RTVI framework implementation for their bots. Where possible, we follow the design pattern established in the Pipecat documentation, which can be found [here](https://docs.pipecat.ai/deployment/pattern).

## Available examples:

- [local](/local) - A useful setup when building or testing clients in local development. This example spawns [Pipecat](https://www.pipecat.ai) bots that connect to your RTVI clients as local Python processes. It also serves as a good starting template for other deployment targets not included in this repository.


---

We would appreciate any pull requests for other cloud providers not included in this repository!