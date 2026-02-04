function wrapLines(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
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
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);

    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#111';
    ctx.font = `${16 * dpr}px system-ui, sans-serif`;
    ctx.textBaseline = 'top';

    const padding = 16 * dpr;
    const lineHeight = 22 * dpr;

    const usableWidth = canvas.width - padding * 2;
    const lines = wrapLines(ctx, text, usableWidth);

    let y = padding;

    for (const line of lines) {
    if (y > canvas.height - padding) break;
    ctx.fillText(line, padding, y);
    y += lineHeight;
    }
}
