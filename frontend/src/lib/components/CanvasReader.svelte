	<script lang="ts">
		import { onMount } from 'svelte';
		import { render } from '$lib/canvas/render';

		export let text = '';
		let canvas: HTMLCanvasElement;

		export let noise = 0;
		export let stripes = 0;

		export let fontSize = 16;
		export let lineSpacing = 0;
		export let charSpacing = 0;
		export let wordSpacing = 0;

		export let perturbationColor = '#000000';
		export let stripeAngle = 45;
		export let stripeMode: 'global' | 'between-lines' = 'global';

		export let opacityJitter = 0;
		export let seed = 0;

		function redraw() {
			if (!canvas) return;

			render(canvas, {
				text,
				seed,
				noise,
				stripes,
				fontSize,
				lineSpacing,
				charSpacing,
				wordSpacing,
				perturbationColor,
				stripeAngle,
				stripeMode,
				opacityJitter
			});
		}

		export function exportPng() {
			if (!canvas) return;

			const noisePct = Math.round(noise * 100);
			const stripesPct = Math.round(stripes * 100);
			const opacityPct = Math.round(opacityJitter * 100);

			const url = canvas.toDataURL('image/png');
			const a = document.createElement('a');
			a.href = url;

			const filename =
				`fs=${fontSize}` +
				`_ls=${lineSpacing}` +
				`_cs=${charSpacing}` +
				`_ws=${wordSpacing}` +
				`_noise=${noisePct}` +
				`_stripes=${stripesPct}` +
				`_oj=${opacityPct}` +
				`_seed=${seed}.png`;

			a.download = filename;
			a.click();
		}

		$: text, redraw();
		$: noise, redraw();
		$: stripes, redraw();
		$: fontSize, redraw();
		$: lineSpacing, redraw();
		$: charSpacing, redraw();
		$: wordSpacing, redraw();
		$: perturbationColor, redraw();
		$: stripeAngle, redraw();
		$: stripeMode, redraw();
		$: opacityJitter, redraw();
		$: seed, redraw();

		onMount(() => {
			redraw();
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