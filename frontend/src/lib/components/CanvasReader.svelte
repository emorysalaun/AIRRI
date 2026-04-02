	<script lang="ts">
		import { onMount } from 'svelte';
		import { drawText, measureTextHeight } from '$lib/canvas/drawText';
		import { drawNoise } from '$lib/canvas/perturbations/noise';
		import { drawStripes, drawBetweenLineStripes } from '$lib/canvas/perturbations/stripes';

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

		let lastHeight = -1;

		function redraw() {
			if (!canvas) return;

			const neededH = measureTextHeight(canvas, text, fontSize, lineSpacing, wordSpacing, charSpacing);
			if (neededH !== lastHeight) {
				canvas.style.height = `${neededH}px`;
				lastHeight = neededH;
			}

			const layout = drawText(
				canvas,
				text,
				fontSize,
				lineSpacing,
				wordSpacing,
				charSpacing,
				opacityJitter
			);
			if (!layout) return;

			const ctx = canvas.getContext('2d');
			if (!ctx) return;

			const rect = canvas.getBoundingClientRect();
			const color = perturbationColor;

			if (noise > 0) {
				drawNoise(ctx, rect.width, rect.height, noise, color);
			}

			if (stripes > 0) {
				if (stripeMode === 'global') {
					drawStripes(ctx, rect.width, rect.height, stripes, 8, 8, color, stripeAngle);
				} else {
					drawBetweenLineStripes(
						ctx,
						rect.width,
						layout.lineYs,
						fontSize,
						layout.lineHeight,
						stripes,
						color
					);
				}
			}
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
				`_oj=${opacityPct}.png`;

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