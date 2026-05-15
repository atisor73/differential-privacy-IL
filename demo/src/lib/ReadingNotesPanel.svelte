<script>
  export let notes = [];
</script>

<article class="panel">
  <div class="panel-header">
    <div>
      <h2>Notes</h2>
      <p>These cues keep the visual metaphor closer to the way DP outputs actually behave.</p>
    </div>
  </div>
  <ul>
    {#each notes as note}
      <li>{note}</li>
    {/each}
  </ul>
</article>

<style>
  .panel {
    margin: 0;
    padding: 1rem;
    border-radius: var(--panel-radius);
    background: var(--paper);
    box-shadow: var(--shadow);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 0.8rem;
  }

  h2 {
    margin: 0;
    font-family: "Fraunces", serif;
    font-size: 1.35rem;
  }

  p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    line-height: 1.45;
  }

  ul {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--muted);
    line-height: 1.6;
  }
</style>
