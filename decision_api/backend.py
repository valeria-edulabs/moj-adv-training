"""
Gemini Decisions API demo (backend only).

Docs: https://aistudio.google.com/docs/decisions-api

The Decisions API does NOT generate text. You send:
    - input:     shared content (text / PDF / image / audio / video)
    - questions: a map of typed questions (up to 1,000), evaluated in parallel
and get back one *calibrated* answer per question:
    - noul   -> yes/no         -> answer.noul (P(yes)), answer.confidence
    - choice -> pick an option -> answer.choice, answer.probabilities, answer.confidence
    - score  -> ordinal scale  -> answer.score, answer.legend, answer.probabilities, answer.confidence

Output tokens are always 0 - you pay only for input tokens.

Setup:
    pip install -U google-genai python-dotenv     # SDK >= 3.2
    GEMINI_API_KEY=... in .env
"""
import base64
import json
import sys

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = "gemini-decision-1"
CONFIDENCE_THRESHOLD = 0.7

# The Decisions API lives on v1beta
client = genai.Client(http_options={"api_version": "v1beta"})


# ---------------------------------------------------------------------------
# 1. Yes/No question (noul)
# ---------------------------------------------------------------------------
def demo_noul():
    print("\n=== 1. noul (yes/no) ===")
    result = client.decisions.create(
        model=MODEL,
        input="I was called up for 4 months of reserve duty (Miluim) and could not pay my tax installment.",
        questions={
            "is_hardship": {
                "type": "noul",
                "instructions": "Does the citizen describe a genuine hardship that prevented payment?",
                # criteria is optional for noul
                "criteria": {
                    "true_description": "A concrete external event (illness, reserve duty, war damage, job loss)",
                    "false_description": "No reason, or a vague/personal-preference reason",
                },
            }
        },
    )
    answer = result.answers["is_hardship"]
    print(f"P(yes)={answer.noul:.2f} confidence={answer.confidence:.2f}")


# ---------------------------------------------------------------------------
# 2. Multiple-choice question (choice) + confidence gating
# ---------------------------------------------------------------------------

def route_inquiry(text: str) -> str:
    result = client.decisions.create(
        model=MODEL,
        input=text,
        questions={
            "department": {
                "type": "choice",
                "instructions": "Which department should handle this citizen inquiry?",
                "criteria": {
                    "income_tax": "Questions about income tax, brackets, refunds, tax credit points",
                    "vat": "Questions about VAT (Ma'am), invoices, VAT reporting",
                    "real_estate": "Purchase tax, betterment tax (Mas Shevach), property sales",
                    "payments": "Debts, installment plans, payment deferrals",
                    "other": "",  # empty description is allowed
                },
            }
        },
    )
    answer = result.answers["department"]
    print(f"  choice={answer.choice} confidence={answer.confidence:.2f}")
    print(f"  probabilities={ {k: round(v, 3) for k, v in answer.probabilities.items()} }")

    # Calibrated confidence lets plain code decide when to trust the model
    if answer.confidence >= CONFIDENCE_THRESHOLD:
        return answer.choice
    return "human_review"


def demo_choice():
    print("\n=== 2. choice + confidence gating ===")
    inquiries = [
        "I sold my apartment in Haifa last month, how much Mas Shevach will I pay?",
        "I need to split my outstanding debt into 12 monthly payments.",
        "Hi, I have a question.",  # ambiguous -> should go to human review
    ]
    for text in inquiries:
        print(f"\n> {text}")
        print(f"  ROUTED TO: {route_inquiry(text)}")


# ---------------------------------------------------------------------------
# 3. Ordinal scale (score)
# ---------------------------------------------------------------------------
def demo_score():
    print("\n=== 3. score (ordinal scale) ===")
    result = client.decisions.create(
        model=MODEL,
        input="This is the third time I'm writing! Nobody answers and you charged me a fine I don't owe!!!",
        questions={
            "urgency": {
                "type": "score",
                "instructions": "How urgent is it to respond to this message?",
                # lowest -> highest
                "criteria": ["Not urgent", "Normal", "Urgent", "Critical"],
            }
        },
    )
    answer = result.answers["urgency"]
    # score is a probability-weighted average of level indices -> can be between levels
    top_level = max(answer.probabilities, key=answer.probabilities.get)
    normalized = answer.score / (len(answer.legend) - 1)
    print(f"score={answer.score:.2f} (normalized {normalized:.2f}) confidence={answer.confidence:.2f}")
    print(f"most likely level: {top_level} -> {answer.legend[top_level]}")


# ---------------------------------------------------------------------------
# 4. Many questions over one shared input (one call, evaluated in parallel)
# ---------------------------------------------------------------------------
def demo_multi_question():
    print("\n=== 4. multiple questions in one request ===")
    request = {
        "request_id": "R-003",
        "taxpayer_type": "company",
        "amount_due_ils": 950_000,
        "requested_months": 24,
        "previous_defaults": 0,
        "reason": "Our main warehouse was damaged by a rocket strike. Insurance claim is pending.",
    }
    result = client.decisions.create(
        model=MODEL,
        # input can be a list of blocks; adjacent text blocks are concatenated
        # with NO separator, so add your own "\n"
        input=[
            {"type": "text", "text": "Payment deferral request:\n"},
            {"type": "text", "text": json.dumps(request, ensure_ascii=False) + "\n"},
        ],
        questions={
            "has_valid_reason": {
                "type": "noul",
                "instructions": "Is the stated reason a documented hardship (war damage, illness, reserve duty, job loss)?",
            },
            "mentions_legal_risk": {
                "type": "noul",
                "instructions": "Does the request mention fraud, bankruptcy or legal proceedings?",
            },
            "recommendation": {
                "type": "choice",
                "instructions": "What should the tax officer do with this request? "
                                "Companies asking for more than 18 months must be escalated.",
                "criteria": {
                    "approve": "Grant the deferral as requested",
                    "reject": "Deny the deferral",
                    "escalate": "Send to a senior officer for manual review",
                },
            },
            "risk": {
                "type": "score",
                "instructions": "How risky is it for the state to grant this deferral?",
                "criteria": ["Low", "Medium", "High"],
            },
        },
    )

    for key, answer in result.answers.items():
        if answer.type == "noul":
            print(f"{key:20s} P(yes)={answer.noul:.2f}  conf={answer.confidence:.2f}")
        elif answer.type == "choice":
            print(f"{key:20s} {answer.choice:8s}     conf={answer.confidence:.2f}")
        elif answer.type == "score":
            print(f"{key:20s} score={answer.score:.2f}   conf={answer.confidence:.2f}")

    u = result.usage
    print(f"usage: input={u.total_input_tokens} output={u.total_output_tokens} total={u.total_tokens}")


# ---------------------------------------------------------------------------
# 5. Multimodal input: decisions over a PDF document
# ---------------------------------------------------------------------------
def demo_pdf(pdf_path: str):
    print(f"\n=== 5. PDF input ({pdf_path}) ===")
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    result = client.decisions.create(
        model=MODEL,
        input=[
            {"type": "text", "text": "Document submitted by a taxpayer:\n"},
            {"type": "document", "data": pdf_b64, "mime_type": "application/pdf"},
        ],
        questions={
            "doc_type": {
                "type": "choice",
                "instructions": "What kind of document is this?",
                "criteria": {
                    "medical_certificate": "",
                    "military_reserve_order": "",
                    "invoice": "",
                    "bank_statement": "",
                    "other": "",
                },
            },
            "is_signed": {"type": "noul", "instructions": "Is the document signed or stamped?"},
        },
    )
    doc_type = result.answers["doc_type"]
    signed = result.answers["is_signed"]
    print(f"doc_type={doc_type.choice} (conf {doc_type.confidence:.2f})")
    print(f"is_signed P(yes)={signed.noul:.2f}")


if __name__ == "__main__":
    demo_noul()
    # demo_choice()
    # demo_score()
    # demo_multi_question()
    # if len(sys.argv) > 1:  # python decision_api/backend.py path/to/file.pdf
    #     demo_pdf(sys.argv[1])
