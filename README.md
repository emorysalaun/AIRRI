# AIRRI — AI Resilient Reading Interface

AIRRI is an **experimental SvelteKit application** for rendering text onto a canvas and applying **perceptual perturbations** (such as noise, masking, and stripes) to study AI-resilient reading and obfuscation techniques.


---

## Requirements

- **Node.js v22.19.0** (tested)
- **npm** (bundled with Node)


## Installation

From the project root:

```bash
npm install
```

This installs all required SvelteKit, Vite, and development dependencies.

---

## Running the Project (Development)

Start the local development server:

```bash
npm run dev
```


Open that URL in your browser.

---


## Quick Tutorial

### 1. Enter Text
On the left side of the interface, type or paste text into the input box.  
As you type, the text is immediately rendered onto the canvas on the right.

### 2. Apply Perturbations
Below the text input are sliders for each available perturbation:

- **Noise** – adds random visual noise over the text
- **Stripes** – placeholder (no effect yet)
- **Mask** – placeholder (no effect yet)

Move a slider away from zero to apply that perturbation.  
Higher values increase the strength of the effect.

Multiple perturbations can be adjusted independently (effects are layered).

### 3. View Canvas Output
The right panel displays the final rendered result on an HTML `<canvas>`:
- Base text is drawn first
- Perturbations are drawn as overlay layers
- Updates happen in real time as text or sliders change

To remove an effect, set its slider back to zero, or press the clear button.

---

## Project Structure (High Level)

```text
src/
├─ routes/
│  └─ +page.svelte                 # Main application layout
├─ lib/
│  ├─ components/
│  │  ├─ TextInput.svelte          # Text input panel
│  │  └─ CanvasReader.svelte       # Canvas rendering + perturbations
│  └─ canvas/
│     ├─ drawText.ts               # Base text rendering logic
│     └─ perturbations/
│        └─ noise.ts               # Noise perturbation (others WIP)
```

---

## Features

- Text input rendered onto an HTML `<canvas>`
- Slider-controlled perturbations:
  - Noise (implemented)
  - Stripes (placeholder)
  - Mask (placeholder)
- Real-time redraw on text or slider changes

---

