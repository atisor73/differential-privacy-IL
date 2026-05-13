<script>
  import { populationChange, safeRatio } from './metrics.js';

  export let records = [];
  export let epsilonIndex = 0;
  export let level = 'county';
  export let epsilonValue = 0.5;

  let sortMode = 'change';
  let displayed = [];

  $: displayed = records
    .slice()
    .sort((left, right) =>
      sortMode === 'population'
        ? right.truePop - left.truePop
        : Math.abs(populationChange(right, epsilonIndex)) - Math.abs(populationChange(left, epsilonIndex))
    )
    .slice(0, 12);

  function labelFor(record) {
    if (level === 'county') {
      return `County ${record.geoid.slice(-3)}`;
    }
    if (level === 'tract') {
      return `Tract ${record.geoid.slice(-6)}`;
    }
    return `Block ${record.geoid.slice(-4)}`;
  }

  function segments(record, released) {
    const pop = released ? record.adjPop[epsilonIndex] : record.truePop;
    const white = released ? record.adjWhite[epsilonIndex] : record.white;
    const black = released ? record.adjBlack[epsilonIndex] : record.black;
    const asian = released ? record.adjAsian[epsilonIndex] : record.asian;
    const other = released ? record.adjOther[epsilonIndex] : record.other;
    return [
      { label: 'White', tone: '#7d2230', value: safeRatio(white, pop) },
      { label: 'Black', tone: '#565f6b', value: safeRatio(black, pop) },
      { label: 'Asian', tone: '#9b8f86', value: safeRatio(asian, pop) },
      { label: 'Other', tone: '#342c31', value: safeRatio(other, pop) }
    ];
  }
</script>

<article class="panel">
  <div class="panel-header">
    <div>
      <h2>Composition-change tiles</h2>
      <p>
        Each tile compares truth to one simulated released estimate at ε = {epsilonValue.toFixed(2)}. The release
        can push the white share up or down; it should not drift only one way.
      </p>
    </div>
    <div class="segmented">
      <button type="button" class:active={sortMode === 'change'} on:click={() => (sortMode = 'change')}>
        Biggest change
      </button>
      <button type="button" class:active={sortMode === 'population'} on:click={() => (sortMode = 'population')}>
        Biggest places
      </button>
    </div>
  </div>

  <div class="tile-grid">
    {#each displayed as record}
      <article class="tile">
        <div class="tile-header">
          <strong>{labelFor(record)}</strong>
          <span>{Math.round(populationChange(record, epsilonIndex)).toLocaleString()}</span>
        </div>

        <div class="row">
          <span>True</span>
          <div class="bar">
            {#each segments(record, false) as segment}
              <span title={segment.label} style={`width:${segment.value * 100}%;background:${segment.tone};`}></span>
            {/each}
          </div>
        </div>

        <div class="row">
          <span>Published estimate</span>
          <div class="bar">
            {#each segments(record, true) as segment}
              <span title={segment.label} style={`width:${segment.value * 100}%;background:${segment.tone};opacity:0.86;`}></span>
            {/each}
          </div>
        </div>
      </article>
    {/each}
  </div>

  <div class="legend">
    <span><i style="background:#7d2230"></i>White</span>
    <span><i style="background:#565f6b"></i>Black</span>
    <span><i style="background:#9b8f86"></i>Asian</span>
    <span><i style="background:#342c31"></i>Other</span>
  </div>
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

  .panel-header,
  .tile-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .panel-header {
    margin-bottom: 1rem;
  }

  h2 {
    margin: 0;
    font-family: "Fraunces", serif;
    font-size: 1.45rem;
  }

  p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .segmented {
    display: inline-flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  button {
    border: 0;
    border-radius: var(--pill-radius);
    padding: 0.65rem 0.95rem;
    background: rgba(231, 234, 238, 0.92);
    color: var(--ink);
  }

  button.active {
    background: var(--accent);
    color: white;
  }

  .tile-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 0.8rem;
  }

  .tile {
    padding: 0.9rem;
    border-radius: var(--tile-radius);
    background: rgba(231, 234, 238, 0.96);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .tile-header span,
  .row span {
    color: var(--muted);
    font-size: 0.84rem;
  }

  .row {
    display: grid;
    gap: 0.3rem;
    margin-top: 0.7rem;
  }

  .bar {
    display: flex;
    width: 100%;
    height: 14px;
    overflow: hidden;
    border-radius: var(--pill-radius);
    background: rgba(44, 35, 40, 0.08);
  }

  .bar span {
    display: block;
    height: 100%;
  }

  .legend {
    margin-top: 0.9rem;
    display: flex;
    gap: 0.85rem;
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
