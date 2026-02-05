function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
	const lines: string[] = [];

	// Line ending fixing, again
	const paragraphs = text.replace(/\r\n/g, '\n').split('\n');

	// For each word in each line in each paragraph, check if adding it would add too much width.
	for (const paragraph of paragraphs) {
		const words = paragraph.split(' ');
		let currentLine = '';

		for (const word of words) {
			let nextLine: string;

			if (currentLine === '') {
				nextLine = word;
			} else {
				nextLine = currentLine + ' ' + word;
			}

			if (ctx.measureText(nextLine).width <= maxWidth) {
				currentLine = nextLine;
			} else {
				lines.push(currentLine);
				currentLine = word;
			}
		}

		lines.push(currentLine);
	}

	return lines;
}

export function drawText(canvas: HTMLCanvasElement, text: string) {
	const ctx = canvas.getContext('2d');
	if (!ctx) return;

	const dpr = window.devicePixelRatio || 1;
	const rect = canvas.getBoundingClientRect();

	// Drawing buffer size.
	canvas.width = Math.floor(rect.width * dpr);
	canvas.height = Math.floor(rect.height * dpr);

	//draw using CSS pixels
	ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

	// Clear in CSS pixels
	ctx.fillStyle = '#fff';
	ctx.fillRect(0, 0, rect.width, rect.height);

	ctx.fillStyle = '#111';
	ctx.font = `16px system-ui, sans-serif`;
	ctx.textBaseline = 'top';

	const padding = 16;
	const lineHeight = 22;

	const usableWidth = rect.width - padding * 2;
	const lines = wrapLines(ctx, text, usableWidth);

	let y = padding;
	for (const line of lines) {
		if (y > rect.height - padding) break;
		ctx.fillText(line, padding, y);
		y += lineHeight;
	}
}

