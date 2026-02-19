<script lang="ts">
	import { onMount } from 'svelte';
	import { drawText, measureTextHeight } from '$lib/canvas/drawText';
    import {drawNoise} from '$lib/canvas/perturbations/noise';
	import {drawStripes} from '$lib/canvas/perturbations/stripes';

	export let text = '';
	let canvas: HTMLCanvasElement;

    export let noise = 0;
    export let stripes = 0;
    export let mask = 0;
	export let fontSize = 16;

	function redraw() {
		if (!canvas) return;

		const neededH = measureTextHeight(canvas, text, fontSize);

		// Dynamically changes the height of the canvas while adding lines.
		canvas.style.height = `${neededH}px`;
		drawText(canvas, text, fontSize);

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

		const rect = canvas.getBoundingClientRect();
	
		// Apply perturbations.
		if (noise > 0) drawNoise(ctx, rect.width, rect.height, noise);
		if (stripes > 0) drawStripes(ctx, rect.width, rect.height, stripes, 8, 8, 45, 'rgba(0, 0, 0, 1)');	
	}

	export function exportPng(){
		if (!canvas) return;

		const noisePct = Math.round(noise * 100);
  		const stripesPct = Math.round(stripes * 100);
  		const maskPct = Math.round(mask * 100);
		
		const url = canvas.toDataURL('image/png');
		const a = document.createElement('a');
		a.href = url;
		const filename = `noise_${noisePct}_stripes_${stripesPct}_mask_${maskPct}.png`;
		a.download = filename
		a.click();
	}

	$: text, redraw();
    $: noise, redraw();
    $: stripes, redraw();
    $: mask, redraw();
	$: fontSize, redraw();

	onMount(() => {
		redraw();
		const ro = new ResizeObserver(() => redraw());
		ro.observe(canvas);
		return () => ro.disconnect();
	});
</script>

<section class="panel">
	<h2>Canvas Output</h2>
	<div class="scroll">
		<!-- assings the canvas made here as the canvas variable-->
		<canvas bind:this={canvas}></canvas>
	</div>
</section>

<style>
	.panel {
		display: flex;
		flex-direction: column;
		gap: 8px;
		min-height: 0;
	}

	.scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		border: 1px solid #ddd;
		border-radius: 8px;
		background: white;
	}

	canvas {
		display: block;
		width: 100%;
	}
</style>
