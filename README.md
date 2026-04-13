# LangGraph code generation

Experimental Python project that uses **LangChain** and **LangGraph** to generate Python code from a natural-language requirement, synthesize small test cases, run them, and optionally refine the code when execution fails.

## What it does

1. **Load context** — `main.py` (and variants) crawl [LangGraph documentation](https://python.langchain.com/docs/langgraph/) with `RecursiveUrlLoader` and sort pages for use as background context.
2. **Generate** — An OpenAI chat model produces structured output (`prefix` + `code`) for the given requirement.
3. **Test & execute** — A second structured pass proposes inputs/expected outputs; a third pass wraps the code with assertions; the graph runs the result with `exec()`.
4. **Retry** — On failure, a “finetune” step feeds the error back and regenerates code. A conditional edge decides whether to finish or loop back to generation.

The default demo requirement at the bottom of `main.py` is illustrative; change it to your own task.

## Repository layout

| Path | Role |
|------|------|
| `main.py` | Primary LangGraph workflow (generate → check execution → conditional retry). |
| `main_revise.py` | Revised variant of the same idea (same overall structure). |
| `main0.py`, `main1.py` | Earlier or alternate experiments. |
| `utils.py` | Tavily web search helper; writes `langgraph_doc_url.pickle`. |
| `get_langgraph_doc.py` | Loads LangGraph-related content from GitHub (issues, markdown, notebooks) using a token. |
| `set_envrion.py` | Example environment setup (prefer real env vars instead of committed values). |
| `API_KEYS.py` | Key placeholders used by some scripts — **should be replaced with environment variables** and not committed in real projects. |
| `examples/` | Prompt / example text used for experiments. |
| `langgraph_doc.txt` | Cached or exported doc text (if present from a prior run). |

## Dependencies

Install the libraries implied by the imports, for example:

```bash
pip install langchain langchain-openai langchain-community langgraph beautifulsoup4 tavily-python nbformat nbconvert
```

Exact versions are not pinned in this repo; pin them in your own environment if you need reproducible builds.

## Configuration and security

Several files still embed API keys directly. For any non-throwaway use you should:

- Set `OPENAI_API_KEY` (and optionally LangSmith / LangChain tracing keys) via the environment or a local `.env` that is **gitignored**.
- Use a **GitHub personal access token** only from the environment for `get_langgraph_doc.py`, not a committed module.
- Rotate any keys that have ever been committed to a remote repository.

After moving secrets to the environment, point `ChatOpenAI` and other clients at `os.environ["OPENAI_API_KEY"]` (or your config layer of choice) instead of string literals.

## Running

From the repository root (after installing dependencies and configuring keys):

```bash
python main.py
```

Other entry points:

```bash
python main_revise.py
python get_langgraph_doc.py   # requires GitHub token configuration
```

`Untitled1.ipynb` is a notebook variant of the same exploration.

## Notes

- Graph state uses a `keys` dict holding `requirement`, `generation`, and `error` through the loop.
- Doc loading at import time means the first run may be slow and requires network access unless you refactor to cache documents locally.
