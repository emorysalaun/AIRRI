<script lang="ts">
	import { onMount } from 'svelte';
	import { render, type RenderConfig } from '$lib/canvas/render';

	let canvas: HTMLCanvasElement;

	onMount(() => {
		const api = (config: RenderConfig) => {
			render(canvas, config);
			return canvas.toDataURL('image/png');
		};

		(window as Window & { render?: typeof api }).render = api;
		document.documentElement.dataset.ready = 'true';

		return () => {
			delete (window as Window & { render?: typeof api }).render;
		};
	});
</script>

<canvas bind:this={canvas}></canvas>

<style>
	:global(body) {
		margin: 0;
	}

	canvas {
		display: block;
	}
</style>
