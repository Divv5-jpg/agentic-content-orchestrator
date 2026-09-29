````markdown
# Agentic Content Orchestrator

A **LangGraph-based agentic workflow** for research-aware technical content generation, featuring conditional routing, structured planning, parallel execution, evidence grounding, and LangSmith observability.

## Architecture

```text
User Topic
    │
    ▼
┌─────────────┐
│    Router   │
└──────┬──────┘
       │
       ├── Closed Book ───────────────┐
       │                              │
       └── Research Required          │
               │                      │
               ▼                      │
          Tavily Search               │
               │                      │
               ▼                      │
            Evidence ─────────────────┤
                                      ▼
                              ┌──────────────┐
                              │ Orchestrator │
                              └──────┬───────┘
                                     │
                              Fan-out Workers
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
                 Worker 1         Worker 2         Worker 3 ...
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                                ┌─────────┐
                                │ Reducer │
                                └────┬────┘
                                     ▼
                              Final Markdown
````

## Features

* **Conditional research routing** — determines whether external research is required for a topic.
* **Structured planning** — generates a typed five-section writing plan using Pydantic.
* **Parallel generation** — uses LangGraph fan-out to generate sections independently.
* **Evidence grounding** — passes retrieved research evidence to workers for factual grounding and citations.
* **Deterministic assembly** — restores section order and combines generated sections into the final document.
* **Structured LLM outputs** — uses Pydantic schemas to validate model responses.
* **Workflow observability** — uses LangSmith to trace and debug the end-to-end workflow.
* **Streamlit interface** — provides an interface for generating and downloading Markdown blogs.

## Workflow

1. **Router** classifies the topic as `closed_book`, `hybrid`, or `open_book`.
2. **Research** optionally retrieves and normalizes web evidence using Tavily.
3. **Orchestrator** creates a structured five-section writing plan.
4. **Workers** generate individual sections through LangGraph fan-out.
5. **Reducer** restores section order and produces the final Markdown document.

## Observability

The workflow is integrated with **LangSmith** for end-to-end tracing and debugging.

LangSmith provides visibility into:

* Router decisions
* Research and tool execution
* Structured planning
* Individual worker executions
* LLM inputs and outputs
* Overall LangGraph workflow execution

This allows individual stages of the workflow to be inspected instead of treating the LLM pipeline as a black box.

## Tech Stack

| Component              | Technology           |
| ---------------------- | -------------------- |
| Workflow orchestration | LangGraph            |
| LLM                    | Groq                 |
| Model                  | `openai/gpt-oss-20b` |
| Web research           | Tavily               |
| Structured schemas     | Pydantic             |
| Frontend               | Streamlit            |
| Observability          | LangSmith            |
| Language               | Python               |

## Screenshots

### Streamlit Interface

![Streamlit Interface](screenshots/frontend.png)

### LangSmith Workflow Trace

![LangSmith Workflow Trace](screenshots/langsmith.png)

## Engineering Highlights

* Conditional workflow routing with LangGraph
* Typed state management using `TypedDict`
* Structured LLM outputs validated with Pydantic
* Parallel section generation using LangGraph fan-out
* Research evidence normalization and deduplication
* URL-based evidence grounding
* Deterministic aggregation and section ordering using reducers
* End-to-end workflow observability with LangSmith
* Secure API configuration using environment variables

## Project Structure

```text
agentic-content-orchestrator/
├── bwa_backend.py
├── frontend.py
├── screenshots/
│   ├── frontend.png
│   └── langsmith.png
├── .gitignore
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/agentic-content-orchestrator.git
cd agentic-content-orchestrator
```

### 2. Create and activate a virtual environment

Windows:

```cmd
python -m venv myenv
myenv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=blog_generator
```

### 5. Run the application

```bash
streamlit run frontend.py
```

## Future Improvements

* Section-level streaming in the UI
* Stronger source-quality and citation validation
* Persistent generation history
* Retry and failure handling for individual workers
* Automated evaluation of generated content

```
```
