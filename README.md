# AIRRI — AI Resilient Reading Interface

AIRRI is a SvelteKit application for generating human-readable, machine-resistant text images. It renders instructor-provided text onto an HTML canvas and applies configurable typographic and image-level perturbations for research on AI-resistant educational content.

---

## Requirements

- Node.js 22.x
- npm

---

## Installation

Install the project dependencies:

```bash
npm install
```

---

## Running the Development Server

Start the development server:

```bash
npm run dev
```

Open the displayed local URL (typically `http://localhost:5173`) in your browser.

---

## Usage

1. Enter or paste text into the editor.
2. Adjust the available perturbation settings using the sliders.
3. The canvas updates automatically as settings change.
4. Export the rendered image if desired.

---

## Project Structure

```text
src/
├── routes/
│   └── +page.svelte          # Main application
├── lib/
│   ├── components/           # UI components
│   ├── canvas/               # Rendering logic
│   ├── perturbations/        # Image-level perturbations
│   └── typography/           # Text rendering utilities
```

---

## Current Features

- HTML canvas text rendering
- Configurable typographic perturbations
- Image-level perturbations
- Real-time rendering preview
- Export rendered images

---

## Purpose

AIRRI was developed as a research platform for evaluating techniques that reduce automated text extraction while maintaining human readability. It is intended for experimentation and evaluation rather than production use.
