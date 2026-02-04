<script lang="ts">
  import { onMount } from 'svelte';
  import { drawText } from '$lib/canvas/drawText';

  export let text = '';
  let canvas: HTMLCanvasElement;

  function redraw() {
    if (canvas) drawText(canvas, text);
  }

  // When text changes, trigger a redraw.
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
  <canvas bind:this={canvas}></canvas>
</section>

<style>
  .panel { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  canvas { flex: 1; width: 100%; border: 1px solid #ddd; border-radius: 8px; background: white; display: block; }
</style>
