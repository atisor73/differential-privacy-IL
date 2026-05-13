<script>
  export let epsilonLabel = '0.5';
  export let changeMode = 'absolute';
  export let scopeLabel = 'Statewide';
  export let summary = null;

  function formatPopulation(value) {
    return Math.round(value).toLocaleString();
  }

  function formatMaybePercent(value) {
    return `${(value * 100).toFixed(1)}%`;
  }
</script>

<article class="panel summary-panel">
  <span class="scope-label">{scopeLabel}</span>
  <span class="chip">ε = {epsilonLabel}</span>
  {#if summary}
    <div class="summary-stat">
      <span class="eyebrow">Units</span>
      <strong>{summary.count.toLocaleString()}</strong>
    </div>
    <div class="summary-stat">
      <span class="eyebrow">Mean change</span>
      <strong>
        {changeMode === 'percent'
          ? formatMaybePercent(summary.meanChange)
          : formatPopulation(summary.meanChange)}
      </strong>
    </div>
    <div class="summary-stat">
      <span class="eyebrow">Mean |change|</span>
      <strong>
        {changeMode === 'percent'
          ? formatMaybePercent(summary.meanAbsoluteChange)
          : formatPopulation(summary.meanAbsoluteChange)}
      </strong>
    </div>
    <div class="summary-stat">
      <span class="eyebrow">Mean true % white</span>
      <strong>{formatMaybePercent(summary.meanWhiteShare)}</strong>
    </div>
  {/if}
</article>

<style>
  .panel {
    margin: 0;
    padding: 0.75rem 0.85rem;
    border-radius: var(--panel-radius);
    background: var(--paper);
    box-shadow: var(--shadow);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .summary-panel {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem 1rem;
  }

  .scope-label {
    font-family: "Fraunces", serif;
    font-size: 1rem;
    color: var(--ink);
    margin-right: 0.2rem;
  }

  .chip {
    font-size: 0.74rem;
    color: var(--muted);
    padding: 0.3rem 0.55rem;
    background: rgba(231, 234, 238, 0.94);
    border-radius: var(--pill-radius);
  }

  .summary-stat {
    display: grid;
    gap: 0.08rem;
    min-width: max-content;
  }

  .eyebrow {
    display: block;
    font-size: 0.67rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 0.3rem;
  }

  strong {
    display: block;
    font-size: 0.98rem;
    color: var(--ink);
  }
</style>
