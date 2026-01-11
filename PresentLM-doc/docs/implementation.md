---
sidebar_position: 5
---

# Demo Implementation

PresentLM is implemented as a modular, AI-driven presentation system that synchronizes slide progression, spoken narration, and real-time interaction.

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '2em 0', textAlign: 'center' }}>
  <strong>The system treats slides as temporal reference points, shaping:</strong>
  <ul style={{ listStyle: 'none', padding: 0, margin: '1em 0 0 0' }}>
    <li>✓ What is said</li>
    <li>✓ When it is said</li>
    <li>✓ How explanations unfold</li>
  </ul>
</div>

---

## Core Components

<div style={{ display: 'flex', justifyContent: 'center' }}>
  <img src="/PresentLM/img/DemoImpl.png" alt="DemoImpl" style={{ width: '100%', height: 'auto' }} />
</div>

### 1. Slide Parser

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> Document Parser, optionally VLMs for image-heavy slides
  <br/><br/>
  <strong>Function:</strong> Extracts textual and structural information from uploaded slide decks (PDF, PPT).
</div>

### 2. Narration Generator

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> LLM (Large Language Model)
  <br/><br/>
  <strong>Function:</strong> Generates structured, slide-aligned spoken explanations using slides and optional notes as grounding context.
</div>

### 3. Text-to-Speech (TTS)

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> TTS Engine
  <br/><br/>
  <strong>Function:</strong> Converts narration into natural speech with controlled pacing and emphasis.
</div>

### 4. Temporal Synchronization Engine

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> Custom Synchronization System
  <br/><br/>
  <strong>Function:</strong> Automatically advances slides in sync with narration.
</div>

### 5. Interaction Handler

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> Event Management System
  <br/><br/>
  <strong>Function:</strong> Detects user intent (interrupt, pause, resume, question) and routes input to the appropriate system component.
</div>

### 6. Speech-to-Text

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> STT (Speech-to-Text) Engine
  <br/><br/>
  <strong>Function:</strong> Generates the question text from the user's audio input.
</div>

### 7. Question Handler

<div style={{ padding: '1.5em', borderRadius: '8px', backgroundColor: 'var(--ifm-color-emphasis-100)', margin: '1em 0' }}>
  <strong>Technology:</strong> LLM (Large Language Model)
  <br/><br/>
  <strong>Function:</strong> Answers user questions in a way that updates or augments the existing narration state, allowing temporal synchronization to resume without breaking presentation flow.
</div>

---

## System Architecture

```mermaid
graph TD
    A[User Uploads Slides] --> B[Slide Parser]
    B --> C[Narration Generator]
    C --> D[TTS Engine]
    D --> E[Temporal Sync Engine]
    E --> F[Presentation Playback]
    F --> G{User Interaction?}
    G -->|Question| H[Speech-to-Text]
    H --> I[Question Handler]
    I --> E
    G -->|Continue| E
```

<div style={{ textAlign: 'center', fontStyle: 'italic', margin: '1em 0' }}>
  System flow diagram showing the interaction between components
</div>
