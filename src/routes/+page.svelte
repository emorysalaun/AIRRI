<script lang="ts">
	import TextInput from '$lib/components/TextInput.svelte';
	import CanvasReader from '$lib/components/CanvasReader.svelte';

	let text = '';
	let reader: CanvasReader | null = null;

	// 0..1 intensities
	let noise = 0;
	let stripes = 0;
	let mask = 0;

	// Font stuff
	let fontSize = 16;
	let lineSpacing = 0;
	let charSpacing = 0;
	let wordSpacing = 0;


	function clearPerturbations() {
		noise = 0;
		stripes = 0;
		mask = 0;
		lineSpacing = 0;
		charSpacing = 0;
		wordSpacing = 0;
		fontSize = 16;
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
			<div class="row">
				<label for="noise">Noise: {noise.toFixed(2)}</label>
				<input id="noise" type="range" min="0" max="1" step="0.01" bind:value={noise} />
			</div>

			<div class="row">
				<label for="stripes">Stripes: {stripes.toFixed(2)}</label>
				<input id="stripes" type="range" min="0" max="1" step="0.01" bind:value={stripes} />
			</div>

			<div class="row">
				<label for="mask">Mask: {mask.toFixed(2)}</label>
				<input id="mask" type="range" min="0" max="1" step="0.01" bind:value={mask} />
			</div>
			<div class="row">
				<label for="fontSize">Font Size: {fontSize.toFixed(2)}</label>
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



			<button type="button" on:click={clearPerturbations}>Clear</button>
			<button type="button" on:click={exportAsPng}>Export</button>
		</div>
	</div>

	<CanvasReader bind:this={reader} {text} {noise} {stripes} {mask} {fontSize} {lineSpacing} {charSpacing} {wordSpacing}/>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		padding: 16px;
		height: calc(100vh - 32px);
		box-sizing: border-box;
	}

	.left {
		display: flex;
		flex-direction: column;
		gap: 12px;
		min-height: 0;
	}

	.controls {
		border: 1px solid #ddd;
		border-radius: 8px;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.row {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	input[type='range'] {
		width: 100%;
	}


.inputWrap {
	flex: 1;        /* <-- THIS is the fix */
	min-height: 0;  /* <-- required in constrained layouts */
}

/* If TextInput uses a textarea (very likely) */
.inputWrap :global(textarea) {
	height: 100%;
	width: 100%;
	resize: none;
	box-sizing: border-box;
}
</style>
