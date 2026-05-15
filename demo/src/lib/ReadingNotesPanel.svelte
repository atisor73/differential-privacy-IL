<script>
  export let notes = [];
</script>

<article class="panel">
  <div class="panel-header">
    <div>
      <h2>Notes</h2>
      <p>The visual shows the user the results of DP simulations, in particular how
        racial composition varies at a block, tract, and county level at varying epsilons. 
        This can be useful for troubleshooting
      pathological algorithmic behavior, and compare different approaches or modifications to the algorithm.
      Here we compare the unconstrained case, where noising takes place with rounding, and the constrained case,
      where at each on-spline level, the vector
      <span class="math">[x<sub>W</sub>, x<sub>B</sub>, x<sub>A</sub>, x<sub>O</sub>]</span>
      is rounded to the nearest simplex satisfying
      the original total population constraint <span class="math">x<sub>W, noise</sub> + x<sub>B, noise </sub> + x<sub>A, noise</sub> + x<sub>O, noise</sub> = P<sub>original</sub></span>.</p>
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

  .math {
    font-family: "Iowan Old Style", "Times New Roman", serif;
    color: var(--ink);
    white-space: nowrap;
  }

  ul {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--muted);
    line-height: 1.6;
  }
</style>
