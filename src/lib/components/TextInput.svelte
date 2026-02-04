<script lang="ts">
  export let value = '';
</script>

<section class="panel">
  <h2>Input</h2>
  <textarea bind:value spellcheck="false"></textarea>
</section>

<style>
  .panel { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  textarea { flex: 1; width: 100%; resize: none; padding: 12px; border: 1px solid #ddd; border-radius: 8px; }
</style>
