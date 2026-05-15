<script>
  import {
    countChange,
    formatCountyLabel,
    raceColor,
    raceLabel,
    raceSubjectLabel,
    releasedRaceCount,
    safeRatio,
    trueRaceCount
  } from './metrics.js';

  export let selectedRecord = null;
  export let epsilonIndex = 0;
  export let changeMode = 'absolute';
  export let level = 'county';
  export let selectedRace = 'white';
  export let embedded = false;

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

  function activeRaceLabel() {
    return raceLabel(selectedRace);
  }

  function activeRaceSubject() {
    return raceSubjectLabel(selectedRace);
  }

  function activeRaceColor() {
    return raceColor(selectedRace);
  }

  function composition(record, released) {
    const pop = released ? record.adjPop[epsilonIndex] : record.truePop;
    const white = released ? record.adjWhite[epsilonIndex] : record.white;
    const black = released ? record.adjBlack[epsilonIndex] : record.black;
    const asian = released ? record.adjAsian[epsilonIndex] : record.asian;
    const other = released ? record.adjOther[epsilonIndex] : record.other;
    return [
      { label: 'White', value: safeRatio(white, pop), tone: raceColor('white') },
      { label: 'Black', value: safeRatio(black, pop), tone: raceColor('black') },
      { label: 'Asian', value: safeRatio(asian, pop), tone: raceColor('asian') },
      { label: 'Other', value: safeRatio(other, pop), tone: raceColor('other') }
    ];
  }
</script>

<section class="stack">
  <article class:panel={!embedded} class="detail-shell">
    <div class="panel-header">
      <div>
        <h2>{recordLabel(selectedRecord)}</h2>
        {#if !selectedRecord}
          <p>Use the map to inspect a unit’s released and true population counts.</p>
        {/if}
      </div>
    </div>

    {#if selectedRecord}
      <div class="compare-grid">
        <section>
          <div class="bar-row">
            <div class="stat-row">
              <span class="eyebrow">True {activeRaceSubject()} count</span>
              <strong style={`color:${activeRaceColor()};`}>{formatPopulation(trueRaceCount(selectedRecord, selectedRace))}</strong>
            </div>
            <div class="stacked-bar" aria-hidden="true">
              {#each composition(selectedRecord, false) as segment}
                <span style={`width:${segment.value * 100}%;background:${segment.tone};`}></span>
              {/each}
            </div>
          </div>
        </section>

        <section>
          <div class="bar-row">
            <div class="stat-row">
              <span class="eyebrow">Released {activeRaceSubject()} count</span>
              <strong style={`color:${activeRaceColor()};`}>{formatPopulation(releasedRaceCount(selectedRecord, epsilonIndex, selectedRace))}</strong>
            </div>
            <div class="stacked-bar" aria-hidden="true">
              {#each composition(selectedRecord, true) as segment}
                <span style={`width:${segment.value * 100}%;background:${segment.tone};`}></span>
              {/each}
            </div>
          </div>
        </section>
      </div>

      <div class="legend">
        <span><i style={`background:${raceColor('white')}`}></i>White</span>
        <span><i style={`background:${raceColor('black')}`}></i>Black</span>
        <span><i style={`background:${raceColor('asian')}`}></i>Asian</span>
        <span><i style={`background:${raceColor('other')}`}></i>Other</span>
      </div>
    {/if}
  </article>
</section>

<style>
  .stack {
    display: grid;
    gap: 1rem;
  }

  .detail-shell {
    margin: 0;
  }

  .panel {
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
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
  }

  strong {
    font-size: 1rem;
  }

  .stat-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.8rem;
    min-width: 210px;
  }

  .compare-grid {
    display: grid;
    gap: 0.9rem;
  }

  .bar-row {
    display: grid;
    grid-template-columns: minmax(210px, 250px) minmax(0, 1fr);
    gap: 1rem;
    align-items: center;
  }

  .stacked-bar {
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

  @media (max-width: 720px) {
    .bar-row {
      grid-template-columns: 1fr;
      gap: 0.45rem;
    }

    .stat-row {
      min-width: 0;
    }
  }

</style>
