<script lang="ts">
	import TextInput from '$lib/components/TextInput.svelte';
	import CanvasReader from '$lib/components/CanvasReader.svelte';

	let text = '';
	let reader: CanvasReader | null = null;

	let noise = 0;
	let stripes = 0;

	let fontSize = 16;
	let lineSpacing = 0;
	let charSpacing = 0;
	let wordSpacing = 0;

	let perturbationColor = '#000000';
	let stripeAngle = 45;
	let stripeMode: 'global' | 'between-lines' = 'global';

	let opacityJitter = 0;

	function clearPerturbations() {
		noise = 0;
		stripes = 0;
		fontSize = 16;
		lineSpacing = 0;
		charSpacing = 0;
		wordSpacing = 0;
		perturbationColor = '#000000';
		stripeAngle = 45;
		stripeMode = 'global';
		opacityJitter = 0;
	}

	function exportAsPng() {
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
						<label for="stripeMode">Stripe Mode</label>
						<select id="stripeMode" bind:value={stripeMode}>
							<option value="global">Global</option>
							<option value="between-lines">Between Lines</option>
						</select>
					</div>

					<div class="row">
						<label for="stripeAngle">Stripe Angle: {stripeAngle.toFixed(0)}°</label>
						<input id="stripeAngle" type="range" min="0" max="180" step="1" bind:value={stripeAngle} />
					</div>

					<div class="row">
						<label for="perturbationColor">Perturbation Color</label>
						<input id="perturbationColor" type="color" bind:value={perturbationColor} />
					</div>

					<div class="subsection">
						<h4>Opacity Effects</h4>

						<div class="row">
							<label for="opacityJitter">Opacity Jitter: {opacityJitter.toFixed(2)}</label>
							<input
								id="opacityJitter"
								type="range"
								min="0"
								max="1"
								step="0.01"
								bind:value={opacityJitter}
							/>
						</div>
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
		{stripeAngle}
		{stripeMode}
		{opacityJitter}
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

	.subsection {
		border-top: 1px solid #eee;
		padding-top: 10px;
		margin-top: 4px;
	}

	.subsection h4 {
		margin: 0 0 8px 0;
		font-size: 0.95rem;
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

	input[type='range'],
	select {
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