"""Debug script: goi thang LLM judge de xem loi that thay vi bi metrics.py nuot mat.

`evaluate_pipeline()` trong `src/evaluation/metrics.py` bat moi Exception khi goi LLM judge
va fallback sang heuristic, nen khong bao gio thay traceback that. Script nay goi lai
dung logic do (build_llm + with_structured_output(JudgeVerdict)) nhung KHONG bat loi,
de in ra nguyen nhan that.

Chay:
    uv run python script/debug_judge.py
"""

from __future__ import annotations

from core.config import load_settings, normalized_provider
from evaluation.metrics import JudgeVerdict
from retrieval.llm import build_llm


def main() -> None:
    settings = load_settings()
    print(f"LLM_PROVIDER (normalized): {normalized_provider(settings)}")
    print(f"LLM_MODEL: {settings.model_name}")

    prompt = """
Evaluate the model answer against the reference answer.

Question: Who are the authors of the paper 'Test Paper'?
Reference answer: Alice, Bob
Model answer: Alice, Bob

Return:
- score from 1 to 5
- correct = true only when the answer is materially correct
- short reasoning
""".strip()

    print("\nBuilding LLM...")
    llm = build_llm(settings=settings, temperature=0.0)
    print(f"LLM object: {llm!r}")

    print("\nAttaching structured output (JudgeVerdict) and invoking...")
    structured_llm = llm.with_structured_output(JudgeVerdict, method="function_calling")
    result = structured_llm.invoke(prompt)

    print("\nSUCCESS. Result:")
    print(result)


if __name__ == "__main__":
    main()
