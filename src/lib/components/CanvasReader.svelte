<script lang="ts">
  import { onMount } from 'svelte';
  import { drawText } from '$lib/canvas/drawText';

  export let text = '';
  let canvas: HTMLCanvasElement;

  function redraw() {
    if (!canvas) return;

    const lines = (text || '').split('\n').length || 1;
    const h = 32 + lines * 24;

    // Dynamically changes the height of the canvas while adding lines.
    canvas.style.height = `${h}px`; 
    drawText(canvas, text);
  }

  $: text, redraw();

  onMount(() => {
    redraw();
    const onResize = () => redraw();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  });
</script>

<section class="panel">
  <h2>Canvas Output</h2>
  <div class="scroll">
    <canvas bind:this={canvas}></canvas>
  </div>
</section>

<style>
  .panel { display: flex; flex-direction: column; gap: 8px; min-height: 0; }

  .scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: white;
  }

  canvas { display: block; width: 100%; }
</style>
