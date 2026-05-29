export function drawNoise(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  amount: number,
  color: string = '#000000',
  random: () => number = Math.random
) {
  ctx.save();
  ctx.globalAlpha = amount;
  ctx.fillStyle = color;

  const dots = Math.floor(((w * h) / 625) * amount);
  for (let i = 0; i < dots; i++) {
    const x = random() * w;
    const y = random() * h;
    const r = 0.8 + random() * 1.6;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}