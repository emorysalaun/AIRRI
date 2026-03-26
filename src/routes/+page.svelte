<script lang="ts">
	import TextInput from '$lib/components/TextInput.svelte';
	import CanvasReader from '$lib/components/CanvasReader.svelte';

	let text = '';
	let reader: CanvasReader | null = null;

	let noise = 0;
	let stripes = 0;
	let mask = 0;

	let fontSize = 16;
	let lineSpacing = 0;
	let charSpacing = 0;
	let wordSpacing = 0;

	let perturbationColor = '#000000';
	let perturbationAlpha = 1;
	let stripeAngle = 45;

	function clearPerturbations() {
		noise = 0;
		stripes = 0;
		mask = 0;
		lineSpacing = 0;
		charSpacing = 0;
		wordSpacing = 0;
		fontSize = 16;
		perturbationColor = '#000000';
		perturbationAlpha = 1;
		stripeAngle = 45;
	}

	function exportAsPng() {
		console.log('reader:', reader);
		reader?.exportPng();
	}
</script>

<svelte:head>
	<title>AIRRI - AI Resilient Reading Interface</title>
</svelte:head>

<div class="grid">
	<div class="left">
		<div class="inputWrap">
			<TextInput bind:value={text} />
		</div>

		<div class="controls">
			<details class="panel">
				<summary>Perturbation</summary>

				<div class="panelContent">
					<div class="row">
						<label for="noise">Noise: {noise.toFixed(2)}</label>
						<input id="noise" type="range" min="0" max="1" step="0.01" bind:value={noise} />
					</div>

					<div class="row">
						<label for="stripes">Stripes: {stripes.toFixed(2)}</label>
						<input id="stripes" type="range" min="0" max="1" step="0.01" bind:value={stripes} />
					</div>

					<div class="row">
						<label for="stripeAngle">Stripe Angle: {stripeAngle.toFixed(0)}°</label>
						<input id="stripeAngle" type="range" min="0" max="180" step="1" bind:value={stripeAngle} />
					</div>

					<div class="row">
						<label for="perturbationColor">Perturbation Color</label>
						<input id="perturbationColor" type="color" bind:value={perturbationColor} />
					</div>

					<div class="row">
						<label for="perturbationAlpha">Perturbation Opacity: {perturbationAlpha.toFixed(2)}</label>
						<input
							id="perturbationAlpha"
							type="range"
							min="0"
							max="1"
							step="0.01"
							bind:value={perturbationAlpha}
						/>
					</div>
				</div>
			</details>

			<details class="panel">
				<summary>Font and Spacing</summary>

				<div class="panelContent">
					<div class="row">
						<label for="fontSize">Font Size: {fontSize.toFixed(0)}</label>
						<input id="fontSize" type="range" min="1" max="48" step="1" bind:value={fontSize} />
					</div>

					<div class="row">
						<label for="lineSpacing">Line Spacing: {lineSpacing.toFixed(0)}px</label>
						<input id="lineSpacing" type="range" min="0" max="40" step="1" bind:value={lineSpacing} />
					</div>

					<div class="row">
						<label for="charSpacing">Character Spacing: {charSpacing.toFixed(1)}px</label>
						<input id="charSpacing" type="range" min="0" max="10" step="0.5" bind:value={charSpacing} />
					</div>

					<div class="row">
						<label for="wordSpacing">Word Spacing: {wordSpacing.toFixed(0)}px</label>
						<input id="wordSpacing" type="range" min="0" max="30" step="1" bind:value={wordSpacing} />
					</div>
				</div>
			</details>

			<div class="buttonRow">
				<button type="button" on:click={clearPerturbations}>Clear</button>
				<button type="button" on:click={exportAsPng}>Export</button>
			</div>
		</div>
	</div>

	<CanvasReader
		bind:this={reader}
		{text}
		{noise}
		{stripes}
		{fontSize}
		{lineSpacing}
		{charSpacing}
		{wordSpacing}
		{perturbationColor}
		{perturbationAlpha}
		{stripeAngle}
	/>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		padding: 16px;
		height: 100vh;
		box-sizing: border-box;
		overflow: hidden;
	}

	.left {
		display: flex;
		flex-direction: column;
		gap: 12px;
		min-height: 0;
		overflow-y: auto;
	}

	.controls {
		border: 1px solid #ddd;
		border-radius: 8px;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		flex: 0 0 auto;
	}

	.panel {
		border: 1px solid #ddd;
		border-radius: 8px;
		padding: 8px 10px;
	}

	.panel summary {
		cursor: pointer;
		font-weight: 600;
	}

	.panelContent {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-top: 10px;
	}

	.row {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.buttonRow {
		display: flex;
		gap: 8px;
	}

	input[type='range'] {
		width: 100%;
	}

	.inputWrap {
		flex: 0 0 auto;
		min-height: 220px;
	}

	.inputWrap :global(textarea) {
		height: 220px;
		width: 100%;
		resize: vertical;
		box-sizing: border-box;
	}
</style>