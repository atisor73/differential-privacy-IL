<script>
  import { onDestroy } from 'svelte';
  import { simulateRecordRelease } from './simulate.js';

  export let records = [];
  export let epsilonValue = 0.5;
  export let level = 'county';
  export let scopeLabel = 'Statewide';

  let frameIndex = 0;
  let autoplay = true;
  let intervalId = null;
  let spotlight = [];
  let frames = [];
  let frameTotals = [];

  $: spotlight = records
    .slice()
    .sort((left, right) => right.truePop - left.truePop)
    .slice(0, level === 'county' ? 12 : 16);

  $: frames = Array.from({ length: 20 }, (_, frame) =>
    spotlight.map((record) =>
      simulateRecordRelease(record, epsilonValue, ['releases', level, scopeLabel, frame])
    )
  );

  $: frameTotals = frames.map((frame) =>
    frame.reduce((sum, record) => sum + record.simulatedPop, 0)
  );

  $: syncInterval();

  function syncInterval() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    if (autoplay && frames.length) {
      intervalId = setInterval(() => {
        frameIndex = (frameIndex + 1) % frames.length;
      }, 1000);
    }
  }

  onDestroy(() => {
    if (intervalId) {
      clearInterval(intervalId);
    }
  });

  function cardLabel(record) {
    if (level === 'county') {
      return `County ${record.geoid.slice(-3)}`;
    }
    if (level === 'tract') {
      return `Tract ${record.geoid.slice(-6)}`;
    }
    return `Block ${record.geoid.slice(-4)}`;
  }

  function formatNumber(value) {
    return Math.round(value).toLocaleString();
  }

  function deltaColor(value) {
    return value >= 0 ? '#7d2230' : '#6f7884';
  }
</script>

<section class="panel-stack">
  <article class="panel">
    <div class="panel-header">
      <div>
        <h2>Repeated releases / possible outputs</h2>
        <p>
          One fixed underlying dataset, twenty possible releases. Each frame resamples a DP-style output at the
          current ε to show that the release is a distribution, not a single immutable answer.
        </p>
      </div>
      <div class="controls">
        <button type="button" class:active={autoplay} on:click={() => (autoplay = !autoplay)}>
          {autoplay ? 'Pause' : 'Play'}
        </button>
        <span class="chip">Frame {frameIndex + 1} / {frames.length}</span>
      </div>
    </div>

    <input type="range" min="0" max={Math.max(0, frames.length - 1)} step="1" bind:value={frameIndex} />

    <div class="timeline">
      {#each frameTotals as total, index}
        <button
          type="button"
          class:active={index === frameIndex}
          style={`height:${48 + (Math.abs(total - frameTotals[0]) / Math.max(1, Math.max(...frameTotals.map((value) => Math.abs(value - frameTotals[0]))))) * 52}px;`}
          aria-label={`Jump to frame ${index + 1}`}
          on:click={() => (frameIndex = index)}
        ></button>
      {/each}
    </div>
  </article>

  <article class="panel">
    <div class="panel-header">
      <div>
        <h2>Current frame</h2>
        <p>{scopeLabel} · showing the largest units in view.</p>
      </div>
      <span class="chip">ε = {epsilonValue}</span>
    </div>

    <div class="grid">
      {#each frames[frameIndex] ?? [] as record}
        <article class="tile">
          <div class="tile-header">
            <strong>{cardLabel(record)}</strong>
            <span style={`color:${deltaColor(record.simulatedChange)}`}>{record.simulatedChange >= 0 ? '+' : ''}{formatNumber(record.simulatedChange)}</span>
          </div>
          <div class="metric-row">
            <span>True pop</span>
            <strong>{formatNumber(record.truePop)}</strong>
          </div>
          <div class="metric-row">
            <span>Released pop</span>
            <strong>{formatNumber(record.simulatedPop)}</strong>
          </div>
          <div class="bar-shell" aria-hidden="true">
            <span class="bar true" style={`width:${Math.min(100, (record.truePop / Math.max(1, spotlight[0]?.truePop ?? 1)) * 100)}%`}></span>
            <span class="bar released" style={`width:${Math.min(100, (record.simulatedPop / Math.max(1, spotlight[0]?.truePop ?? 1)) * 100)}%`}></span>
          </div>
        </article>
      {/each}
    </div>
  </article>
</section>

<style>
  .panel-stack {
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

  .panel-header,
  .controls,
  .tile-header,
  .metric-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
  }

  .panel-header {
    align-items: flex-start;
    margin-bottom: 0.85rem;
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

  .chip {
    font-size: 0.82rem;
    color: var(--muted);
    padding: 0.45rem 0.7rem;
    background: rgba(231, 234, 238, 0.94);
    border-radius: var(--pill-radius);
  }

  input[type="range"] {
    width: 100%;
    accent-color: var(--accent);
  }

  .timeline {
    margin-top: 1rem;
    display: grid;
    grid-template-columns: repeat(20, minmax(0, 1fr));
    gap: 0.35rem;
    align-items: end;
  }

  .timeline button {
    width: 100%;
    min-height: 48px;
    border-radius: 8px;
    padding: 0;
    background: rgba(125, 34, 48, 0.18);
  }

  .timeline button.active {
    background: linear-gradient(180deg, #7d2230 0%, #565f6b 100%);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.8rem;
  }

  .tile {
    padding: 0.9rem;
    border-radius: var(--tile-radius);
    background: rgba(231, 234, 238, 0.96);
    border: 1px solid rgba(44, 35, 40, 0.08);
  }

  .tile span {
    color: var(--muted);
    font-size: 0.88rem;
  }

  .tile strong {
    color: var(--ink);
  }

  .metric-row {
    margin-top: 0.45rem;
  }

  .bar-shell {
    margin-top: 0.8rem;
    display: grid;
    gap: 0.35rem;
  }

  .bar {
    display: block;
    height: 10px;
    border-radius: 6px;
  }

  .bar.true {
    background: rgba(111, 120, 132, 0.48);
  }

  .bar.released {
    background: rgba(125, 34, 48, 0.72);
  }
</style>
