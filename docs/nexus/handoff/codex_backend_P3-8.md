# Codex handoff — P3-8 Reality Checker remaining hazards #3+

**Owner**: Codex session
**Source of truth**: `03_evidence_audit.md` (Reality Checker analysis · hazards numbered)
**Status**: **STUB** · blocked on founder triage. Cannot execute until founder reads `03_evidence_audit.md` and decides which hazards beyond #1 (P2-1) and #2 (P2-2) belong in W3 vs W4+.
**Time budget**: TBD per founder triage (each hazard ≈ 0.5-1 day; could be 2 days or 5 days total)

---

## 0. What you build

P2-1 closed Reality Checker hazard #1 (`analysis_returned` double-emit).
P2-2 closed hazard #2 (S7/S8 upstream wiring).

`03_evidence_audit.md` carries additional hazards (#3, #4, ...). Each is a discrete risk that the Reality Checker flagged but hasn't been closed yet. This ticket is a placeholder to batch them into W3 if founder triages them as in-scope.

---

## 1. STUB — required founder input

Before Codex can execute, founder must:

1. Open `03_evidence_audit.md` and list **all hazards** that remain open after P2-1 and P2-2 closed (e.g. "hazards #3 through #N")
2. For each, triage:
   - **W3 in-scope** (file as sub-ticket P3-8a / P3-8b / etc.)
   - **W4+ defer** (note in `03_evidence_audit.md` why deferred)
   - **Cut entirely** (note why no longer relevant)
3. Re-write this brief replacing §2 below with concrete hazard list

PM can help: if founder hasn't read `03_evidence_audit.md` recently, schedule 30min review session and PM will turn the discussion into the filled brief.

---

## 2. Per-hazard sub-tickets (placeholder template)

Once founder triages, each in-scope hazard becomes:

### P3-8a — Hazard #N: <description>

- **Source**: `03_evidence_audit.md §N`
- **Risk**: <what breaks if this isn't fixed>
- **Fix sketch**: <approach from Reality Checker's recommendation OR PM proposal>
- **Test surface**: <how Codex would verify>
- **Done-signal**: <observable check_progress.sh probe OR test name>

(Repeat for each in-scope hazard.)

---

## 3. Done-signal (whole P3-8)

For each in-scope sub-ticket:
- Either fixed with new test in `tests/test_<scope>.py`
- OR explicitly punted to W4 with rationale appended to `03_evidence_audit.md §N`

P3-8 closes when **every remaining Reality Checker hazard** is either fixed or has an explicit deferral note. The Reality Checker doc should not have unaddressed hazards floating after this ticket.

---

## 4. NOT in this ticket

- New hazards discovered after P3-8 starts — file as P4-X
- Hazards from other reviewer docs (Karpathy, Buffett, etc.) — those have separate review cycles
- Production deployment hardening — that's P3-7's scope

---

## 5. PM notes

- This is the "cleanup the audit doc" ticket. Healthy debt-management pattern: every sprint, look back at the last review doc and either fix or explicitly defer.
- Codex is the right owner because:
  - Each hazard typically has a concrete fix + test pattern
  - Reality Checker documentation usually contains enough detail for execution without judgment calls
- If a hazard requires architectural judgment (not just a fix), reassign that sub-ticket to Claude.

**Recommended decision (PM)**: founder does the 30min triage early W3 (W3D1 or W3D2). Sub-tickets in-scope land mid-W3; deferral notes land same week.
