<script lang="ts">
	import TextInput from '$lib/components/TextInput.svelte';
	import CanvasReader from '$lib/components/CanvasReader.svelte';

	let text = '';
</script>

<title>AIRRI - AI Resilient Reading Interface</title>

<div class="grid">
	<TextInput bind:value={text} />
	<CanvasReader {text} />
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
</style>
