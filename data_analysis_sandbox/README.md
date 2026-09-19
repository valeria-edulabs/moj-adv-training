# Data Analysis Agent with Docker Sandbox Backend

This project demonstrates an advanced Data Analysis Agent built with **`deepagents.create_deep_agent`**, running inside an isolated **`DockerSandboxBackend`** container with **Human-in-the-Loop (HITL)** verification and rich visual rendering (Plotly charts & DataFrames).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                       │
│    (Chat UI, Metrics, HITL Approval Card, Rich Visualizer) │
└──────────────────────────────┬──────────────────────────────┘
                               │ stream / resume_stream
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                deepagents.create_deep_agent                 │
│         - Model: ChatGoogleGenerativeAI (gemini-flash-lite) │
│         - FilesystemMiddleware (execute, read, write, etc.) │
│         - HumanInTheLoopMiddleware (interrupt_on={"execute"})│
│         - MemorySaver Checkpointer                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   DockerSandboxBackend                      │
│             (Subclasses BaseSandbox in deepagents)          │
│                                                             │
│   - Image: data-analysis-sandbox:latest                     │
│   - Isolation: --network none, memory: 512m, cpus: 1.0      │
│   - Preloaded: products_stock_data.csv                      │
│   - Host Protection: Zero host disk or host secret bleed    │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

1. **True OS-Level Container Isolation (`DockerSandboxBackend`)**:
   - Subclasses `deepagents.backends.sandbox.BaseSandbox` conforming to `SandboxBackendProtocol`.
   - Each session runs in an ephemeral or dedicated container (`sandbox_da_<thread_id>`).
   - Host secrets (e.g. `GOOGLE_API_KEY`, `LANGCHAIN_API_KEY`) and host disks are never exposed to the container.
   - Network mode set to `--network none` to prevent unauthorized external connections.

2. **Human-In-The-Loop (HITL)**:
   - Configured with `interrupt_on={"execute": True}` on `create_deep_agent`.
   - Any shell command or Python script execution pauses the graph and generates an interactive approval card.
   - The user can:
     - **Approve**: Run the command as-is inside Docker.
     - **Edit & Run**: Modify the script/command before it runs.
     - **Reject**: Abort execution and guide the agent.

3. **Rich Artifact Extraction & Visualization**:
   - Plotly figures exported to `/workspace/chart.json` are automatically parsed and displayed as interactive Plotly charts.
   - Filtered tables exported to `/workspace/result.json` are rendered as interactive Streamlit DataFrames.
   - Dual-tab inspection: "🎨 User View (Interactive Plotly / DataFrame)" and "🤖 Model View (Docker stdout/stderr)".

## Getting Started

### Prerequisites
- Docker Desktop running on your machine.
- Python virtual environment with dependencies installed:
  ```bash
  source .venv/bin/activate
  ```

### Build Docker Sandbox Image (One-Time)
```bash
docker build -t data-analysis-sandbox:latest - << 'EOF'
FROM python:3.11-slim
RUN pip install --no-cache-dir pandas plotly
WORKDIR /workspace
CMD ["tail", "-f", "/dev/null"]
EOF
```

### Launch the Streamlit App
```bash
streamlit run data_analysis_sandbox/frontend.py
```
or with virtual environment python:
```bash
.venv/bin/streamlit run data_analysis_sandbox/frontend.py
```

## Sample Questions to Try

1. **Calculations**:
   > *"What is the average price of the products?"*
2. **Interactive Visualizations**:
   > *"Show me a pie chart with product in stock per category"*
3. **Filtered Data Tables**:
   > *"Show me a table of Electronics with quantity less than 50"*
