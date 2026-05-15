<script>
  export let epsilonLabel = '0.5';
  export let changeMode = 'absolute';
  export let scopeLabel = 'Statewide';
  export let summary = null;
  export let selectedRaceLabel = 'White';
  export let selectedRaceSubject = 'white';
  export let level = 'county';

  function formatPopulation(value) {
    return Math.round(value).toLocaleString();
  }

  function formatMaybePercent(value) {
    return `${(value * 100).toFixed(1)}%`;
  }

  $: compactTractPopulation = level === 'tract' && selectedRaceSubject === 'population';
</script>

<article class="panel summary-panel">
  <span class="chip">ε = {epsilonLabel}</span>
  {#if summary}
    <div class="summary-stat">
      <span class="eyebrow">Units</span>
      <strong>{summary.count.toLocaleString()}</strong>
    </div>
    {#if !compactTractPopulation}
      <div class="summary-stat">
        <span class="eyebrow">Mean {selectedRaceSubject} change</span>
        <strong>
          {changeMode === 'percent'
            ? formatMaybePercent(summary.meanChange)
            : formatPopulation(summary.meanChange)}
        </strong>
      </div>
    {/if}
    <div class="summary-stat">
      <span class="eyebrow">Mean |{selectedRaceSubject} change|</span>
      <strong>
        {changeMode === 'percent'
          ? formatMaybePercent(summary.meanAbsoluteChange)
          : formatPopulation(summary.meanAbsoluteChange)}
      </strong>
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
    flex-wrap: nowrap;
    align-items: center;
    gap: 0.6rem;
    overflow-x: auto;
  }

  .chip {
    font-size: 0.74rem;
    color: var(--muted);
    padding: 0.3rem 0.55rem;
    background: rgba(231, 234, 238, 0.94);
    border-radius: var(--pill-radius);
  }

  .summary-stat {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
    min-width: 0;
    white-space: nowrap;
  }

  .eyebrow {
    font-size: 0.67rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin: 0;
  }

  strong {
    font-size: 0.98rem;
    color: var(--ink);
  }
</style>
