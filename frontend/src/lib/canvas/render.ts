import { drawText, measureTextHeight } from '$lib/canvas/drawText';
import { drawNoise } from '$lib/canvas/perturbations/noise';
import { drawBetweenLineStripes, drawStripes } from '$lib/canvas/perturbations/stripes';
import { createSeededRng, deriveSeed } from '$lib/canvas/seededRng';

export type RenderConfig = {
	text: string;
	seed?: number;
	noise?: number;
	stripes?: number;
	fontSize?: number;
	lineSpacing?: number;
	charSpacing?: number;
	wordSpacing?: number;
	perturbationColor?: string;
	stripeAngle?: number;
	stripeMode?: 'global' | 'between-lines';
	opacityJitter?: number;
	width?: number;
};

const lastHeightByCanvas = new WeakMap<HTMLCanvasElement, number>();

/** Draw one image with the same canvas calls the AIRRI page uses. */
export function render(canvas: HTMLCanvasElement, config: RenderConfig) {
	const text = config.text ?? '';
	const seed = config.seed ?? 0;
	const noise = config.noise ?? 0;
	const stripes = config.stripes ?? 0;
	const fontSize = config.fontSize ?? 16;
	const lineSpacing = config.lineSpacing ?? 0;
	const charSpacing = config.charSpacing ?? 0;
	const wordSpacing = config.wordSpacing ?? 0;
	const perturbationColor = config.perturbationColor ?? '#000000';
	const stripeAngle = config.stripeAngle ?? 45;
	const stripeMode = config.stripeMode ?? 'global';
	const opacityJitter = config.opacityJitter ?? 0;

	if (config.width) {
		canvas.style.width = `${config.width}px`;
	}

	const neededH = measureTextHeight(
		canvas,
		text,
		fontSize,
		lineSpacing,
		wordSpacing,
		charSpacing
	);
	const lastHeight = lastHeightByCanvas.get(canvas) ?? -1;
	if (neededH !== lastHeight) {
		canvas.style.height = `${neededH}px`;
		lastHeightByCanvas.set(canvas, neededH);
	}

	const opacityRandom = createSeededRng(deriveSeed(seed, 'opacityJitter'));
	const layout = drawText(
		canvas,
		text,
		fontSize,
		lineSpacing,
		wordSpacing,
		charSpacing,
		opacityJitter,
		opacityRandom
	);
	if (!layout) return;

	const ctx = canvas.getContext('2d');
	if (!ctx) return;

	const rect = canvas.getBoundingClientRect();
	const color = perturbationColor;

	if (noise > 0) {
		const noiseRandom = createSeededRng(deriveSeed(seed, 'noise'));
		drawNoise(ctx, rect.width, rect.height, noise, color, noiseRandom);
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
