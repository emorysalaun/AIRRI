export function drawStripes(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  amount: number,
  stripeWidth: number = 8,
  gapWidth: number = 8,
  angleDeg: number = 45,
  color: string = 'rgba(255,255,255,0.12)'
) {
  const distanceBetweenStripes = stripeWidth + gapWidth;
  if (distanceBetweenStripes <= 0) return;

  // Create tile for pattern.
  const tile = document.createElement('canvas');
  tile.width = distanceBetweenStripes;
  tile.height = distanceBetweenStripes;

  const t = tile.getContext('2d');
  if (!t) return;

  t.fillStyle = color;
  t.fillRect(0, 0, stripeWidth, distanceBetweenStripes);

  const pattern = ctx.createPattern(tile, 'repeat');
  if (!pattern) return;

  ctx.save();
  ctx.globalAlpha = amount;

  // Rotate around canvas center
  const cx = w / 2;
  const cy = h / 2;
  ctx.translate(cx, cy);
  ctx.rotate((angleDeg * Math.PI) / 180);
  ctx.translate(-cx, -cy);

  ctx.fillStyle = pattern;

  // Overdraw to cover rotation bounds
  const diag = Math.hypot(w, h);
  ctx.fillRect(-diag, -diag, w + diag * 2, h + diag * 2);

  ctx.restore();
}
