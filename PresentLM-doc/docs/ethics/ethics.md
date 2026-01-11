---
sidebar_position: 1
---

# Ethics Brief

## Problem Statement

PresentLM reconstructs spoken explanations from slide decks and allows users to interact conversationally with AI-generated narration. While this enables clarity, accessibility, and reuse of knowledge, it also introduces ethical risks related to **misrepresentation**, **over-authority**, and **trust in AI explanations**.

### Key Ethical Challenges

<div style={{ margin: '1.5em 0' }}>

- **Spoken explanations may be perceived as authoritative**, even when generated from incomplete slides or notes

- **AI-generated narration could unintentionally introduce inaccuracies**, oversimplifications, or biased framing

- **Learners may rely on AI explanations without awareness** of their origin or limitations

- **Automated narration risks replacing, rather than supporting**, human educators or presenters if not clearly framed as assistive

</div>

---

## Failure Points & Key Risks

<div style={{ display: 'flex', flexWrap: 'wrap', gap: '1em', margin: '2em 0' }}>
  <div style={{ flex: '1 1 45%', padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)' }}>
    <h3>Misinformation & Hallucination</h3>
    <p>AI may generate plausible but incorrect explanations, especially when slides lack context.</p>
  </div>
  
  <div style={{ flex: '1 1 45%', padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)' }}>
    <h3>Overconfidence in AI Explanations</h3>
    <p>Users may perceive AI narration as more authoritative than intended, trusting it uncritically.</p>
  </div>
  
  <div style={{ flex: '1 1 45%', padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)' }}>
    <h3>Loss of Authorial Intent</h3>
    <p>Generated narration may not accurately reflect the presenter's original meaning or emphasis.</p>
  </div>
  
  <div style={{ flex: '1 1 45%', padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)' }}>
    <h3>Passive Dependence on AI Narration</h3>
    <p>Over-reliance on AI-generated content may reduce critical engagement with the material.</p>
  </div>
</div>

### These Risks May Result In:

- **Incorrect learning outcomes**, where users internalize flawed explanations
- **Erosion of trust**, if AI explanations contradict original material or user expectations
- **Misuse**, where PresentLM is treated as a definitive source rather than an assistive layer

---

## Safeguards

<div style={{ margin: '2em 0' }}>

| Failure Point | Mitigation Strategy |
|--------------|---------------------|
| **Misinformation / Hallucination** | Slide-grounded narration (RAG-style constraints); optional lecture notes as primary source |
| **Over-authority of AI** | Explicit framing of the AI as a "presenter assistant," not a knowledge authority |
| **Loss of Author Intent** | User-editable narration drafts; ability to regenerate or refine explanations |
| **Misuse** | Clear transparency cues; no autonomous progression without user initiation |

</div>

---

## Human-in-the-Loop Control

PresentLM is explicitly designed to keep the human in control:

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1.5em 0' }}>

✅ **Narration is user-initiated, never automatic**

✅ **Users decide when to listen, pause, replay, or ask questions**

✅ **AI responses are contextual and reactive, not proactive**

</div>

This ensures that PresentLM supports learning and rehearsal **without replacing human judgment**.

---

## Opt-Out

Users can disengage from AI narration or interaction at any time:

<div style={{ display: 'flex', flexWrap: 'wrap', gap: '1em', margin: '2em 0' }}>
  <div style={{ flex: '1 1 30%', padding: '1em', borderRadius: '8px', textAlign: 'center', backgroundColor: 'var(--ifm-color-emphasis-200)' }}>
    <strong>Stop narration instantly</strong>
  </div>
  <div style={{ flex: '1 1 30%', padding: '1em', borderRadius: '8px', textAlign: 'center', backgroundColor: 'var(--ifm-color-emphasis-200)' }}>
    <strong>Disable interactive questioning</strong>
  </div>
  <div style={{ flex: '1 1 30%', padding: '1em', borderRadius: '8px', textAlign: 'center', backgroundColor: 'var(--ifm-color-emphasis-200)' }}>
    <strong>Navigate slides manually without AI involvement</strong>
  </div>
</div>

This ensures that PresentLM remains **optional, assistive, and non-coercive**.
