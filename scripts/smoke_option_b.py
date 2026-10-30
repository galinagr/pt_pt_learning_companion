"""Manual smoke test for Option B against real Meta models.

This exercises the routed text path end to end. Nothing here hardcodes a key;
it reads MODEL_API_KEY from the environment (keep it in a local, git-ignored .env).

Run with real models:

    MODEL_API_KEY=... python scripts/smoke_option_b.py

With no key set it runs against the offline stub so you can see the routing
decisions without spending anything.
"""

import os
import sys

from pt_pt_learning_companion.ai_models import build_text_service

PROMPTS = {
    "translate": "Where is the train station, please?",
    "explore": "a restaurant in Porto",
    "situation": "doctor, appointment, payment",
}

INSTRUCTIONS = {
    "translate": "You translate between English and European Portuguese (pt-PT).",
    "explore": "You write a short, practical guide about a place in European Portuguese and English.",
    "situation": "You prepare a real-life dialog in European Portuguese and English from keywords.",
}


def main() -> int:
    has_key = bool(os.environ.get("MODEL_API_KEY", "").strip())
    print(f"Provider: {'meta' if has_key else 'stub'}")
    if not has_key:
        print("Tip: set MODEL_API_KEY to test real models.\n")

    service = build_text_service()
    for task, prompt in PROMPTS.items():
        for quality in ("standard", "high"):
            result = service.run(
                task=task,
                system=INSTRUCTIONS[task],
                user=prompt,
                quality=quality,
            )
            print(f"[{task} / {quality}]")
            print(
                f"  route: primary={result.plan.primary_model} "
                f"used={result.model_used} escalated={result.escalated} "
                f"fallback={result.used_fallback}"
            )
            print(f"  tokens: {result.total_tokens}  (est units={result.plan.estimated_cost_units})")
            print(f"  text: {result.text[:160].strip()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
