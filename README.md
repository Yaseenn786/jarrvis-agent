# Jarrvis

## Your server, explained

Jarrvis is a lightweight, open-source monitoring tool that watches your server
logs and tells you what broke — and why — in plain English. AI-powered
diagnosis, zero dashboards.

## Why Jarrvis?

Traditional monitoring platforms are built for enterprise scale — priced per
host and per GB of ingested data, and complex enough to need dedicated staff.
For a solo developer, a small startup, or a personal project, that's overkill.
You get charged for terabytes of noise, then still have to interpret the red
graphs yourself.

Jarrvis targets the opposite end:

- **Small to mid-size teams, solo devs, and personal projects**
- **Near-zero running cost** — noise is filtered locally, AI is invoked only
  when something actually breaks
- **Answers, not graphs** — when your app crashes at 2am, Jarrvis tells you
  *what* broke, the *likely cause*,  *one concrete next step* and *from there You can take over and resolve the issue with Jarrvis which will help You  with writing the fix*

## How it works
```
[ Your Server ]                    [ Jarrvis Cloud ]
   Agent  ── events / heartbeats ──►  Hub ──► Claude (diagnosis)
                                       │
                                       ▼
                                  Dashboard + Chat

### The Agent
A lightweight Python process that sits on your server and tails your log
files. It detects error patterns locally , groups
related lines into a single incident (one crash = one alert, not forty), and
ships the event to the Hub. It also sends a heartbeat with CPU / memory / disk
metrics every 60 seconds.

The agent is designed to never harm the host: line-by-line streaming, bounded
memory, no local storage growth.

If the agent process dies, the OS service manager (systemd) restarts it
automatically. If the whole server dies, the Hub notices the missing
heartbeat within minutes and alerts you.

### The Hub
The brain, running on our side (or self-hosted). It receives events, stores
them, and sends each incident — with surrounding log context — to Claude for
diagnosis. The result: a plain-English explanation attached to every event.

The Hub also powers the dashboard and chat, so you can literally ask:
*"how's the app doing?"* — and get an answer grounded in your real events and
live metrics.

### Data philosophy
- Happy-path logs are **never** ingested — only incidents and tiny heartbeats
- Recent data stays hot; older data rolls to cold storage
- The AI is never streamed raw logs — it is invoked per-incident, keeping
  cost near zero

## Status

🚧 Early development. Working today: log tailing, error detection and
grouping, event shipping, AI diagnosis, live dashboard with chat, heartbeat
monitoring. Coming: incident lifecycle (auto-resolve, recurrence detection),
Docker log support, push notifications, deployment tooling.

## License

MIT