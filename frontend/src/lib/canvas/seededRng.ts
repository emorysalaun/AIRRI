/** Mulberry32 PRNG — same seed yields the same sequence of values in [0, 1). */
export function createSeededRng(seed: number): () => number {
	let state = normalizeSeed(seed);

	return () => {
		state = (state + 0x6d2b79f5) >>> 0;
		let t = state;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

export function normalizeSeed(seed: number): number {
	return (Math.trunc(seed) >>> 0) || 0;
}

/** Derive an independent sub-stream from a base seed and a label. */
export function deriveSeed(base: number, salt: string): number {
	let h = normalizeSeed(base);
	for (let i = 0; i < salt.length; i++) {
		h = (Math.imul(31, h) + salt.charCodeAt(i)) | 0;
	}
	return h >>> 0;
}
