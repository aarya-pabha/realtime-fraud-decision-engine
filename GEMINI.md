I # Real-Time Transaction Fraud Engine - Agent Workspace Guidelines

## Project Context
This is a production-grade, real-time transaction fraud detection platform designed for a Data Science portfolio. It features a dual-tier feature store (DuckDB offline + Redis online) and a dynamically scaling LightGBM model. 

## Tech Stack & Architecture Constraints
**CRITICAL: You must adhere to the following technologies. Do not deviate or introduce alternatives unless explicitly instructed by the user.**
- **Frontend**: Dash / Plotly (Do not use React, Streamlit, or Vue)
- **Streaming Ingest**: Apache Kafka / Redpanda (Local Docker Compose Kafka alternative)
- **Feature Store**: Feast with DuckDB (Offline) and Redis (Online)
- **Model Training**: LightGBM tuned with Optuna. Train on the full, unmodified IEEE-CIS dataset.
- **Explainability**: SHAP TreeExplainer (Real-time top-3 reason code generator)
- **Microservice API**: FastAPI with Uvicorn.
- **Drift Monitoring**: Evidently AI (Data & prediction drift on analyst feedback)
- **MLflow Tracking**: Local SQLite backend (`mlruns.db`) and local filesystem. Do not use Postgres or MinIO containers.
- **Orchestration**: Standard Python scripts for data engineering pipelines (Do not use Airflow or Prefect).

## The 4 Key Novelties (Must Implement)
1. **Dual-Tier Feature Store**: Zero-leakage temporal point-in-time joins for training, sub-5ms Redis online.
2. **Dynamic Cost Router**: Adapts thresholding based on transaction dollar value to minimize False Positives & False Negatives.
3. **Real-Time SHAP + Feedback Loop**: Generates human-readable attribution codes. Endpoint for chargeback labels triggering Evidently AI drift.
4. **Empirical SLA Load Benchmark**: Automated Locust stress testing proving sub-25ms p95 latency.

## Testing Strategy
- **DO NOT** write boilerplate unit tests for every file.
- **DO** write targeted Pytest suites for the Feature Store logic and the Dynamic Cost Router.
- **DO** use Locust for load testing the FastAPI endpoints to ensure sub-25ms p95 latency.

## Documentation
- The canonical architectural blueprint is located at `docs/transaction_fraud_ds_portfolio.md`.
- The concrete implementation plan and file structure is located at `docs/implementation_plan.md`.
- **Always read `docs/implementation_plan.md` before creating new files or modifying the system architecture.**

## Coding & Workflow Rules
- **Always follow the `/ponytail` skill** while writing any code (focus on minimal, simplest solutions that work).
- **Always use the Context7 MCP server** (using `resolve-library-id` and `query-docs`) to fetch current documentation for any libraries or frameworks before writing code.
- **Utilize Installed Agent Skills**: You must leverage the following globally installed skills at the relevant junctions:
  - *Implementation & APIs*: `fastapi` & `fastapi-templates` (for Phase 4), `docker-compose-orchestration` (for Phase 7).
  - *Planning & Debugging*: `writing-plans` & `executing-plans` (to structure phase transitions), and `systematic-debugging` (for Kafka/Redis issues).
  - *Testing & Verification*: `test-driven-development` (for DuckDB logic), `python-testing-patterns`, `python-performance-optimization`, and crucially, **`verification-before-completion`** (to mandate passing Locust/Pytest runs before claiming a task is done).
- Document all architectural and technical decisions in a `decision.md` file.
- Document all changes and steps made in a `memory.md` file. **Deleting steps from `memory.md` is strictly forbidden**; you may only append new steps for every change made.
- **Memory Compression:** Use the **`caveman-compress`** skill on `decision.md` and `memory.md` regularly to compress their text into caveman-style and save input tokens across long sessions.

## Version Control & GitHub Best Practices
- **Never commit directly to the `main` branch.** All development must be done on a separate feature or bugfix branch (e.g., `feature/add-cost-router`). Use the **`using-git-worktrees`** skill to isolate feature branches.
- **Follow production-grade GitHub practices:**
  - Open a Pull Request (PR) for all changes before merging to `main`.
  - Use the **`code-review`** and **`code-review-commons`** skills to automate rigorous review of PRs.
  - Ensure all automated checks (like Pytest, Locust tests, and linting) pass on the PR.
  - Require code review and approval before merging.
  - Write clear, descriptive commit messages (e.g., using Conventional Commits).
- **Security & Secret Management:**
  - **Never commit secrets:** Passwords, API keys, access tokens, and sensitive data must never be committed to version control.
  - **Use `.env` files:** Store all local configuration and secrets in a `.env` file. 
  - **Use `.gitignore` properly:** Ensure `.env`, `__pycache__`, virtual environments (`venv/`), local databases (`mlruns.db`), and compiled binaries are excluded.
  - **Provide examples:** Include a `.env.example` file with dummy values.
  - **Enable automated scanning:** Run the **`analyze`** skill on feature branches to prevent secret leaks, and use **`security-patcher`** for automated remediation. Use Dependabot and GitHub Secret Scanning.
