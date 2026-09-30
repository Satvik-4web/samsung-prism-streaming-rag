# Samsung PRISM Theme 4: Streaming Live RAG Architecture

## Team
- **Team Name**: Team Satvik
- **College Name**: [Your College Name]
- **Theme ID**: Theme 4 (Advanced Conversational AI)

## Project Overview
This repository contains the complete source code for our advanced Conversational AI architecture. We built a real-time, low-latency, Streaming Live RAG system that processes voice and text incrementally. 

### Key Features
- **Ultra-Low Latency**: Achieves sub-500ms retrieval latency through our custom Provisional Retrieval Controller.
- **Continuous Voice Streaming**: Utilizes WebSocket streaming and HTML5 Web Speech API to instantly capture voice data and intelligently wait for the user to finish their thought.
- **Anti-Hallucination Grounding**: Implements a strict deterministic verifier that maps generated claims to retrieved chunks, completely eliminating LLM entity hallucination.
- **Rich Chat UI**: WhatsApp-style React frontend with internal RAG state diagnostics visible in real-time.

## Architecture
- **Frontend**: React.js, Vite, TailwindCSS, WebSockets, HTML5 SpeechSynthesis.
- **Backend**: Python 3.12, FastAPI / Uvicorn, Asynchronous Event Loop.
- **Retrievers**: FAISS (Dense) and BM25 (Sparse) running on a local Markdown knowledge base (`data/dev_fixture/samsung_products.md`).

## Setup Instructions
1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd Samsungprism
   ```
2. **Backend Setup**:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # On Windows
   pip install -r requirements.txt
   uvicorn backend.main:app
   ```
3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Demo Video
*(Add your YouTube or Google Drive link here!)*

## Documentation
The official presentation template has been populated and is located in the root of this repository: `Satvik_Team_Submission.pptx`.
