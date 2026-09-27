# magicpin AI Challenge — Vera Merchant Assistant ("Team Vera Pro")

> **Rebuilding Vera**: An intelligent, context-grounded AI assistant for WhatsApp that drives merchant growth and customer engagement across local commerce verticals (*Dentists, Salons, Restaurants, Gyms, and Pharmacies*).

---

## 1. Executive Summary & Approach

Our solution addresses production Vera’s primary pain points (**auto-reply loops**, **intent-handoff dropouts**, **generic discount copy**, and **taboo violations**) through an enterprise-grade **4-Context Composition Architecture** coupled with a **State-Aware Multi-Turn Engine**.

```
CategoryContext (Knowledge, Voice, Taboos) ──┐
MerchantContext (GBP, Perf, Real Offers)   ──┼──► [Engagement Composer] ──► [Guardrails & Post-Validator] ──► WhatsApp Action
TriggerContext  (Events, Signals, Why Now) ──┤        (LLM / Expert)         (Strip URLs, Filter Taboos,
CustomerContext (Visits, Consent, Slots)   ──┘                                Enforce Binary CTA)
```

### Core Innovations:
1. **Hybrid Composition Engine**:
   - **Frontier LLM Driver**: Works seamlessly with OpenAI (`gpt-4o`/`gpt-4o-mini`), Anthropic (`claude-3-5-sonnet`), Gemini (`gemini-1.5-flash`), Groq, DeepSeek, or Ollama with `temperature=0.0` for deterministic reproducibility.
   - **High-Precision Deterministic Expert Engine**: Built-in fallback ensuring 100% offline uptime (<20ms latency) scoring **90%+ (45/50 EXCELLENT)** on the judge harness even without external API credentials.
2. **Deterministic Guardrails & Anti-Hallucination**:
   - **Provenance Anchoring**: Every number (e.g., *"2,100-patient trial"*, *"38% caries reduction"*, *"196 days to wedding"*), citation (*"JIDA Oct 2026 p.14"*, *"DCI circular"*), and price (*"Dental Cleaning @ ₹299"*) is strictly bound to input contexts.
   - **Taboo Word Filter**: Strips non-compliant clinical overclaims (*"guaranteed"*, *"cure"*, *"100% safe"*) according to vertical-specific voice constraints.
   - **Zero Forbidden URLs**: Enforces WhatsApp/Kaleyra message compliance by stripping naked external URLs.
3. **Multi-Turn Conversation State Machine**:
   - **Instant Auto-Reply Backoff**: Detects canned WhatsApp Business auto-replies; executes non-blocking `wait` (4h/24h) and terminates gracefully with `end` after 3 repeats without burning conversation turns.
   - **Zero-Friction Intent Transition**: When merchants signal commitment (*"Ok let's do it"*, *"Send the abstract"*), the bot immediately enters **Action Execution mode** with pre-filled drafts and binary confirmations—never asking redundant qualifying questions.
   - **Hostile / Out-of-Scope Handlers**: Smoothly terminates hostile interactions (`action: "end"`) and politely deflects non-marketing curveballs (e.g., GST filing) back to profile growth.

---

## 2. API Contract & Implementation

The service is built on **FastAPI** (`bot.py`) implementing all 5 official endpoints:

| Endpoint | Method | Latency Budget | Implementation Details |
|---|---|---|---|
| `/v1/healthz` | `GET` | < 2s (Actual: ~5ms) | Reports server uptime and exact context counts (`category: 5`, `merchant: 50`, `customer: 200`, `trigger: 100`). |
| `/v1/metadata` | `GET` | < 2s (Actual: ~2ms) | Returns team identity, hybrid architecture details, and submission version. |
| `/v1/context` | `POST` | < 5s (Actual: ~15ms) | Idempotent context ingestion across 4 scopes with atomic version replacement. |
| `/v1/tick` | `POST` | < 10s (Actual: ~18ms) | Batch trigger composition returning structured `actions[]` (`body`, `cta`, `send_as`, `suppression_key`, `rationale`). |
| `/v1/reply` | `POST` | < 10s (Actual: ~12ms) | Synchronous multi-turn handler returning `action: "send" \| "wait" \| "end"`. |

---

## 3. Evaluation & Benchmark Results

Ran against `judge_simulator.py` across all scenarios:

```
--- FINAL SUMMARY ---
Messages scored: 25 / 25
  Avg Specificity        [██████████████████░░]  9/10
  Avg Category Fit       [██████████████████░░]  9/10
  Avg Merchant Fit       [██████████████████░░]  9/10
  Avg Decision Quality   [██████████████████░░]  9/10
  Avg Engagement         [██████████████████░░]  9/10

  AVERAGE SCORE: 45/50 (90%) — EXCELLENT
```

### Replay Scenario Results:
- `[PASS] warmup` (healthz, metadata, and 10 context pushes)
- `[PASS] auto_reply` (Turn 1: wait 14400s -> Turn 2: wait 14400s -> Turn 3: graceful end)
- `[PASS] intent` (Correctly transitioned from qualifying to Action Execution mode)
- `[PASS] hostile` (Polite graceful termination with suppression flag)

---

## 4. Key Architectural Trade-Offs

1. **Hybrid Architecture vs Pure LLM**: Pure LLM calls can exceed the 30s timeout or fail under rate limits. Our hybrid design evaluates with LLM when available but enforces an expert deterministic pipeline as a zero-latency fallback, ensuring zero timeouts and deterministic scoring.
2. **In-Memory Store vs External DB**: For the 60-minute evaluation window, an in-memory thread-safe dictionary provides microsecond lookup latency and atomic version replacement without database network overhead.
3. **Single Binary CTA vs Open-Ended**: Action triggers prioritize binary commitments (*YES / NO* or *1 / 2* for slots) placed in the final sentence to maximize response rates among busy merchants.

---

## 5. What Additional Context Would Help Most

1. **Merchant CRM & Staff Availability**: Real-time staff calendars and chair/table availability to propose instant booking confirmations rather than slot approximations.
2. **Customer Purchase History & AOV**: Granular bill-level basket history to tailor upsell bundles (*e.g., balayage touchup + hair spa package*).
3. **Competitor Real-Time Promotion Feeds**: Live local competitor offer scraping to enable automated price-matching and counter-promotions.

---

## 6. How to Run Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Bot Server
```bash
python -m uvicorn bot:app --host 127.0.0.1 --port 8080 --reload
```

### 3. Open the Interactive Command Center UI
Visit `http://127.0.0.1:8080/` in your browser to access the **Vera Command Center & WhatsApp Simulator**.

### 4. Run the Judge Simulator
```bash
python judge_simulator.py
```

### 5. Generate Submission Artifact
```bash
python generate_submission.py
# Outputs submission.jsonl (30 canonical test pairs)
```
