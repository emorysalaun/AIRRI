export function drawNoise(
	ctx: CanvasRenderingContext2D,
	canvas: HTMLCanvasElement,
	amount: number
) {
	const w = canvas.clientWidth;
	const h = canvas.clientHeight;

	ctx.save();
    // Intensity of the noise
	ctx.globalAlpha = amount;
	ctx.fillStyle = '#000';

	const dots = Math.floor((w * h) / 2500);
	for (let i = 0; i < dots; i++) {
		const x = Math.random() * w;
		const y = Math.random() * h;
		const r = 0.8 + Math.random() * 1.6;
		ctx.beginPath();
		ctx.arc(x, y, r, 0, Math.PI * 2);
		ctx.fill();
	}

	ctx.restore();
}
