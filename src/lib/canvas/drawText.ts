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

  //Drawing logic
  let y = padding;
  // Normalizes endingss between Windows/Mac/Linux
  for (const line of text.replace(/\r\n/g, '\n').split('\n')) {
    if (y > canvas.height - padding) break;
    ctx.fillText(line, padding, y);
    y += lineHeight;
  }
}
