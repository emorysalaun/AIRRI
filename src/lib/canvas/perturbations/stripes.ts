export function drawStripes(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  amount: number,
  stripeWidth: number = 8,
  gapWidth: number = 8,
  color: string = 'rgba(255,255,255,0.12)',
  stripeAngle: number = 45
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
  ctx.rotate((stripeAngle * Math.PI) / 180);
  ctx.translate(-cx, -cy);

  ctx.fillStyle = pattern;

  // Overdraw to cover rotation bounds
  const diag = Math.hypot(w, h);
  ctx.fillRect(-diag, -diag, w + diag * 2, h + diag * 2);

  ctx.restore();
}
export function drawBetweenLineStripes(
	ctx: CanvasRenderingContext2D,
	w: number,
	lineYs: number[],
	baseLineHeight: number,
	lineSpacing: number,
	amount: number,
	color: string = "rgba(0,0,0,1)"
) {
	if ( lineYs.length < 2) return;

	ctx.save();
	ctx.globalAlpha = amount;
	ctx.fillStyle = color;

	for (let i = 0; i < lineYs.length - 1; i++) {
		const gapY = lineYs[i] + baseLineHeight -6  ;
		const gapHeight = lineSpacing + 8;

		if (gapHeight > 0) {
			ctx.fillRect(0, gapY, w, gapHeight);
		}
	}

	ctx.restore();
}