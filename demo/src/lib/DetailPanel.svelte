<script>
  import { formatCountyLabel, populationChange, safeRatio, whiteShare } from './metrics.js';

  export let selectedRecord = null;
  export let epsilonIndex = 0;
  export let changeMode = 'absolute';
  export let level = 'county';

  function formatPopulation(value) {
    return Math.round(value).toLocaleString();
  }

  function formatMaybePercent(value) {
    return `${(value * 100).toFixed(1)}%`;
  }

  function recordLabel(record) {
    if (!record) {
      return 'Hover a point or region';
    }
    if (level === 'county') {
      return formatCountyLabel(record.geoid);
    }
    if (level === 'tract') {
      return `Tract ${record.geoid}`;
    }
    return `Block ${record.geoid}`;
  }

  function composition(record, released) {
    const pop = released ? record.adjPop[epsilonIndex] : record.truePop;
    const white = released ? record.adjWhite[epsilonIndex] : record.white;
    const black = released ? record.adjBlack[epsilonIndex] : record.black;
    const asian = released ? record.adjAsian[epsilonIndex] : record.asian;
    const other = released ? record.adjOther[epsilonIndex] : record.other;
    return [
      { label: 'White', value: safeRatio(white, pop), tone: '#7d2230' },
      { label: 'Black', value: safeRatio(black, pop), tone: '#565f6b' },
      { label: 'Asian', value: safeRatio(asian, pop), tone: '#9b8f86' },
      { label: 'Other', value: safeRatio(other, pop), tone: '#342c31' }
    ];
  }
</script>

<section class="stack">
  <article class="panel">
    <div class="panel-header">
      <div>
        <h2>{recordLabel(selectedRecord)}</h2>
        <p>
          {#if selectedRecord}
            True % white {formatMaybePercent(whiteShare(selectedRecord))} · Released change
            {changeMode === 'percent'
              ? formatMaybePercent(populationChange(selectedRecord, epsilonIndex, changeMode))
              : formatPopulation(populationChange(selectedRecord, epsilonIndex, changeMode))}
          {:else}
            Use the map or scatterplot to inspect a unit’s composition.
          {/if}
        </p>
      </div>
    </div>

    {#if selectedRecord}
      <div class="compare-grid">
        <section>
          <span class="eyebrow">True population</span>
          <strong>{formatPopulation(selectedRecord.truePop)}</strong>
          <div class="stacked-bar" aria-hidden="true">
            {#each composition(selectedRecord, false) as segment}
              <span style={`width:${segment.value * 100}%;background:${segment.tone};`}></span>
            {/each}
          </div>
        </section>

        <section>
          <span class="eyebrow">Released population</span>
          <strong>{formatPopulation(selectedRecord.adjPop[epsilonIndex])}</strong>
          <div class="stacked-bar" aria-hidden="true">
            {#each composition(selectedRecord, true) as segment}
              <span style={`width:${segment.value * 100}%;background:${segment.tone};`}></span>
            {/each}
          </div>
        </section>
      </div>

      <div class="legend">
        <span><i style="background:#7d2230"></i>White</span>
        <span><i style="background:#565f6b"></i>Black</span>
        <span><i style="background:#9b8f86"></i>Asian</span>
        <span><i style="background:#342c31"></i>Other</span>
      </div>
    {/if}
  </article>
</section>

<style>
  .stack {
    display: grid;
    gap: 1rem;
  }

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

  .eyebrow {
    display: block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 0.3rem;
  }

  strong {
    display: block;
    font-size: 1.2rem;
    color: var(--ink);
  }

  .compare-grid {
    display: grid;
    gap: 0.9rem;
  }

  .stacked-bar {
    margin-top: 0.55rem;
    display: flex;
    width: 100%;
    height: 14px;
    overflow: hidden;
    border-radius: var(--pill-radius);
    background: rgba(44, 35, 40, 0.08);
  }

  .stacked-bar span {
    height: 100%;
    display: block;
  }

  .legend {
    margin-top: 0.85rem;
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
    color: var(--muted);
    font-size: 0.83rem;
  }

  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  .legend i {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
  }

</style>
