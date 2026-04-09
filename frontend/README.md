# IAPH Heritage — Frontend

Web application for the IAPH Heritage RAG assistant. Communicates with the FastAPI backend at `http://localhost:8080`.

## Tech stack

- **Next.js 15** (App Router) — React 19
- **TypeScript**
- **Tailwind CSS** — amber/stone palette
- **Zustand** — client state for chat sessions and routes
- **react-leaflet** — map support for route visualization

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing — 3 feature cards (Chatbot, Routes, Accessibility) |
| `/chat` | Conversational chatbot with session sidebar, message history, and source citations |
| `/routes` | Route generator with smart search input, entity detection, filter sidebar, and saved routes grid |
| `/routes/[id]` | Route detail — interleaved narrative+stop cards, detail panel, two-column layout + interactive guide chatbot |
| `/search` | Faceted heritage search with smart input, entity detection, and filter sidebar |
| `/accessibility` | Lectura Fácil text simplification (basic / intermediate) |

## Structure

```
app/
├── layout.tsx              # Root layout — sticky header nav
├── page.tsx                # Landing page
├── chat/page.tsx           # Chat interface
├── routes/
│   ├── page.tsx            # Route generator + list
│   └── [id]/page.tsx       # Route detail + guide
└── accessibility/page.tsx  # Simplification tool
components/
├── chat/
│   ├── ChatInput.tsx       # Textarea + send button
│   └── MessageBubble.tsx   # Message with source cards
├── routes/
│   ├── RouteCard.tsx       # Route summary card
│   ├── RouteResult.tsx     # Generated route result display
│   ├── RouteSmartInput.tsx # Smart input wrapper for routes
│   ├── RouteStopCard.tsx   # Stop card with image, metadata, and narrative
│   └── RouteDetailPanel.tsx # Detail panel for selected stop
└── shared/
    ├── SmartInput.tsx      # Reusable search input with entity detection highlighting
    ├── FilterSidebar.tsx   # Reusable filter sidebar (heritage type, province, municipality)
    ├── FilterChips.tsx     # Reusable active filter chip display
    └── AssetDetailContent.tsx # Shared heritage asset detail (images, map, metadata) — reused by search and routes
lib/
└── api.ts                  # Typed fetch wrapper for all backend endpoints
store/
├── chat.ts                 # Sessions, messages, sending state
├── routes.ts               # Routes, filters, entity detection, generating state
└── search.ts               # Search results, filters, pagination
```

## Setup

```bash
npm install

# Configure backend URL (defaults to http://localhost:18080/api/v1)
echo "NEXT_PUBLIC_API_URL=http://localhost:18080/api/v1" > .env.local

npm run dev     # http://localhost:3000
npm run build   # production build
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:18080/api/v1` | Backend API base URL |

## API integration

All backend calls go through [`lib/api.ts`](lib/api.ts), which exports typed async clients:

- `rag.query(...)` — single-turn RAG query
- `chat.createSession()` / `chat.sendMessage(...)` — session management
- `routes.generate(...)` / `routes.list()` / `routes.guide(...)` / `routes.suggestions(...)` / `routes.filters(...)` — virtual routes
- `accessibility.simplify(...)` — Lectura Fácil
