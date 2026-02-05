<script lang="ts">
	import { onMount } from 'svelte';
	import { drawText, measureTextHeight } from '$lib/canvas/drawText';
    import {drawNoise} from '$lib/canvas/perturbations/noise';

	export let text = '';
	let canvas: HTMLCanvasElement;

    export let noise = 0;
    export let stripes = 0;
    export let mask = 0;

	function redraw() {
		if (!canvas) return;

		const neededH = measureTextHeight(canvas, text);

		// Dynamically changes the height of the canvas while adding lines.
		canvas.style.height = `${neededH}px`;
		drawText(canvas, text);

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

		const rect = canvas.getBoundingClientRect();
		if (noise > 0) drawNoise(ctx, rect.width, rect.height, noise);

		
	}



	$: text, redraw();
    $: noise, redraw();
    $: stripes, redraw();
    $: mask, redraw();

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
