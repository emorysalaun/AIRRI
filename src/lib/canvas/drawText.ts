	function measureWordWidth(ctx: CanvasRenderingContext2D, word: string, charSpacing: number) {
	if (charSpacing <= 0) return ctx.measureText(word).width;

	let w = 0;
	for (let i = 0; i < word.length; i++) {
		const ch = word[i];
		w += ctx.measureText(ch).width;
		if (i < word.length - 1) w += charSpacing;
	}
	return w;
	}

	export function wrapLines(
	ctx: CanvasRenderingContext2D,
	text: string,
	maxWidth: number,
	wordSpacing: number = 0,
	charSpacing: number = 0
	): string[] {
	const lines: string[] = [];
	const paragraphs = text.replace(/\r\n/g, "\n").split("\n");

	const spaceW = ctx.measureText(" ").width;

	function breakLongWord(word: string) {
		let chunk = "";
		let chunkW = 0;

		for (const ch of word) {
		const chW = ctx.measureText(ch).width;
		const nextW = chunk === "" ? chW : chunkW + charSpacing + chW;

		if (nextW <= maxWidth) {
			chunk += ch;
			chunkW = nextW;
		} else {
			if (chunk.length > 0) lines.push(chunk);

			// start new chunk with this character
			chunk = ch;
			chunkW = chW;
		}
		}

		if (chunk.length > 0) lines.push(chunk);
	}

	for (const paragraph of paragraphs) {
		if (paragraph === "") {
		lines.push("");
		continue;
		}

		const words = paragraph.split(" ");
		let currentWords: string[] = [];
		let currentW = 0;

		for (const word of words) {
		const wordW = measureWordWidth(ctx, word, charSpacing);

		// width if we add this word to current line
		let nextW: number;
		if (currentWords.length === 0) {
			nextW = wordW;
		} else {
			// space + wordSpacing + word width
			nextW = currentW + spaceW + wordSpacing + wordW;
		}

		if (nextW <= maxWidth) {
			currentWords.push(word);
			currentW = nextW;
			continue;
		}

		// Commit current line if it exists
		if (currentWords.length > 0) {
			lines.push(currentWords.join(" "));
			currentWords = [];
			currentW = 0;
		}

		// Put the word on a new line (or break it)
		if (wordW <= maxWidth) {
			currentWords = [word];
			currentW = wordW;
		} else {
			breakLongWord(word);
		}
		}

		lines.push(currentWords.join(" "));
	}

	return lines;
	}



	export function measureTextHeight(canvas: HTMLCanvasElement, text: string, fontSize: number, lineSpacing: number = 0, wordSpacing: number = 0, charSpacing: number = 0,) {
		const ctx = canvas.getContext('2d');
		if (!ctx) return 0;

		const rect = canvas.getBoundingClientRect();

		ctx.font = `${fontSize}px 'Roboto Mono', monospace`;

		const padding = 16;
		const baseLineHeight = fontSize + 4;
		const lineHeight = baseLineHeight + lineSpacing;

		const usableWidth = rect.width - padding * 2;
		const lines = wrapLines(ctx, text, usableWidth);

		return padding * 2 + lines.length * lineHeight;
	}


	function drawLineWithSpacing(
		ctx: CanvasRenderingContext2D,
		line: string,
		x: number,
		y: number,
		charSpacing: number,
		wordSpacing: number
		) {
		const spaceW = ctx.measureText(" ").width;
		const words = line.split(" ");

		for (let wi = 0; wi < words.length; wi++) {
			const word = words[wi];

			if (charSpacing <= 0) {
			ctx.fillText(word, x, y);
			x += ctx.measureText(word).width;
			} else {
			for (let i = 0; i < word.length; i++) {
				const ch = word[i];
				ctx.fillText(ch, x, y);
				x += ctx.measureText(ch).width;
				if (i < word.length - 1) x += charSpacing;
			}
			}

			if (wi < words.length - 1) {
			x += spaceW + wordSpacing;
			}
		}
	}


	export function drawText(
		canvas: HTMLCanvasElement,
		text: string,
		fontSize: number,
		lineSpacing: number = 0,
		wordSpacing: number = 0,
		charSpacing: number = 0
		) {
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const dpr = window.devicePixelRatio || 1;
		const rect = canvas.getBoundingClientRect();

		// Drawing buffer size.
		canvas.width = Math.floor(rect.width * dpr);
		canvas.height = Math.floor(rect.height * dpr);

		// draw using CSS pixels
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

		// Clear in CSS pixels
		ctx.fillStyle = "#fff";
		ctx.fillRect(0, 0, rect.width, rect.height);

		ctx.fillStyle = "#111";
		ctx.font = `${fontSize}px 'Roboto Mono', monospace`;
		ctx.textBaseline = "top";

		const padding = 16;
		const baseLineHeight = fontSize + 4;
		const lineHeight = baseLineHeight + lineSpacing;

		const usableWidth = rect.width - padding * 2;
		const lines = wrapLines(ctx, text, usableWidth, wordSpacing, charSpacing);

		let y = padding;
		for (const line of lines) {
			if (y > rect.height - padding) break;
			drawLineWithSpacing(ctx, line, padding, y, charSpacing, wordSpacing);
			y += lineHeight;
		}
	}
