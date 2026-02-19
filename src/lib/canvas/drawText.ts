	export function wrapLines(
	ctx: CanvasRenderingContext2D,
	text: string,
	maxWidth: number
	): string[] {
	const lines: string[] = [];
	const paragraphs = text.replace(/\r\n/g, "\n").split("\n");

	function breakLongWord(word: string) {
		// Split a long token into chunks that fit.
		let chunk = "";
		for (const ch of word) {
		const next = chunk + ch;
		if (ctx.measureText(next).width <= maxWidth) {
			chunk = next;
		} else {
			if (chunk.length > 0) lines.push(chunk);
			chunk = ch;
		}
		}
		if (chunk.length > 0) lines.push(chunk);
	}

	for (const paragraph of paragraphs) {
		if (paragraph === "") {
		// For blank line preservation.
		lines.push("");
		continue;
		}

		const words = paragraph.split(" ");
		let currentLine = "";

		for (const word of words) {
			let nextLine = "";

			// If the line is empty, don't add a leading space.
			if (currentLine === "") {
				nextLine = word;
			} else {
				// Otherwise we add a space before the next word.
				nextLine = currentLine + " " + word;
			}

			if (ctx.measureText(nextLine).width <= maxWidth) {
				currentLine = nextLine;
				continue;
			}
			


		if (ctx.measureText(nextLine).width <= maxWidth) {
			currentLine = nextLine;
			continue;
		}

		// commit current line if it exists
		if (currentLine !== "") {
			lines.push(currentLine);
			currentLine = "";
		}

		// place the word on a new line
		if (ctx.measureText(word).width <= maxWidth) {
			currentLine = word;
		} else {
			// if word is too long. break it.
			breakLongWord(word);
			currentLine = "";
		}
		}

		lines.push(currentLine);
	}

	return lines;
	}


	export function measureTextHeight(canvas: HTMLCanvasElement, text: string, fontSize: number) {
		const ctx = canvas.getContext('2d');
		if (!ctx) return 0;

		const rect = canvas.getBoundingClientRect();

		ctx.font = `${fontSize}px 'Roboto Mono', monospace`;

		const padding = 16;
		const lineHeight = fontSize + 4;

		const usableWidth = rect.width - padding * 2;
		const lines = wrapLines(ctx, text, usableWidth);

		return padding * 2 + lines.length * lineHeight;
	}

	export function drawText(canvas: HTMLCanvasElement, text: string, fontSize: number) {
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
		ctx.font = `${fontSize}px 'Roboto Mono', monospace`;
		ctx.textBaseline = 'top';

		const padding = 16;
		const lineHeight = fontSize + 4;

		const usableWidth = rect.width - padding * 2;
		const lines = wrapLines(ctx, text, usableWidth);

		let y = padding;
		for (const line of lines) {
			if (y > rect.height - padding) break;
			ctx.fillText(line, padding, y);
			y += lineHeight;
		}
	}

