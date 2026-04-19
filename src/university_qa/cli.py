"""CLI entry point: python -m university_qa.cli "<question>"."""

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="university-qa",
        description="Answer natural-language questions about the university database.",
    )
    parser.add_argument("question", help="Natural-language question to answer.")
    parser.add_argument("--db", default=None, help="Override database path.")
    parser.add_argument("--model", default=None, help="Override LLM model name.")
    parser.add_argument("--trace", action="store_true", help="Print LangSmith run URL on exit.")
    parser.add_argument("--debug", action="store_true", help="Print full final state.")
    args = parser.parse_args()

    from university_qa.composition import build_app
    from university_qa.config import Settings

    overrides: dict[str, object] = {}
    if args.db:
        overrides["db_path"] = args.db
    if args.model:
        # model arg overrides whichever provider is active
        overrides["anthropic_model"] = args.model
        overrides["openai_model"] = args.model

    try:
        settings = Settings(**overrides)  # type: ignore[call-arg]
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        app = build_app(settings)
    except RuntimeError as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        final_state = app.invoke({"question": args.question})
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        sys.exit(1)

    answer = final_state.get("answer") or "(no answer produced)"
    print(answer)

    if args.debug:
        print("\n--- debug state ---")
        debug = {k: v for k, v in final_state.items() if v is not None}
        print(json.dumps(debug, default=str, indent=2))

    if args.trace:
        print("\nLangSmith tracing: enable LANGSMITH_TRACING=true and LANGSMITH_API_KEY.")


if __name__ == "__main__":
    main()
