<script lang="ts">
	export let value = '';
</script>

<section class="panel">
	<h2>Input</h2>
	<textarea bind:value />
</section>

<style>
	.panel {
		display: flex;
		flex-direction: column;
		gap: 8px;
		height: 100%;
		min-height: 0;
	}

	textarea {
		flex: 1;
		min-height: 0;
		width: 100%;
		resize: none;
		box-sizing: border-box;
	}
</style>
