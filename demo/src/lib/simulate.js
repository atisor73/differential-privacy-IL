const RACE_FIELDS = ['white', 'black', 'asian', 'other'];

export function hashSeed(parts) {
  const input = Array.isArray(parts) ? parts.join('|') : String(parts);
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleLaplace(scale, rng) {
  const uniform = Math.max(1e-9, Math.min(1 - 1e-9, rng()));
  const centered = uniform - 0.5;
  return -scale * Math.sign(centered) * Math.log(1 - 2 * Math.abs(centered));
}

export function signedNoisyCount(value, epsilon, seedParts) {
  const safeEpsilon = Math.max(0.01, Number(epsilon) || 0.01);
  const rng = mulberry32(hashSeed(seedParts));
  const scale = 1 / safeEpsilon;
  return Math.round(value + sampleLaplace(scale, rng));
}

export function noisyCount(value, epsilon, seedParts) {
  return Math.max(0, signedNoisyCount(value, epsilon, seedParts));
}

function allocateCounts(total, counts) {
  if (total <= 0) {
    return Object.fromEntries(RACE_FIELDS.map((field) => [field, 0]));
  }

  const positiveSum = RACE_FIELDS.reduce((sum, field) => sum + Math.max(0, counts[field] ?? 0), 0);
  if (positiveSum <= 0) {
    const fallback = Object.fromEntries(RACE_FIELDS.map((field) => [field, 0]));
    fallback.white = total
    return fallback;
  }

  const base = {};
  const remainders = [];
  let assigned = 0;

  for (const field of RACE_FIELDS) {
    const share = Math.max(0, counts[field] ?? 0) / positiveSum;
    const exact = total * share;
    const floorValue = Math.floor(exact);
    base[field] = floorValue;
    assigned += floorValue;
    remainders.push({ field, remainder: exact - floorValue });
  }

  remainders.sort((left, right) => right.remainder - left.remainder);
  let remaining = total - assigned;
  let index = 0;
  while (remaining > 0) {
    base[remainders[index % remainders.length].field] += 1;
    remaining -= 1;
    index += 1;
  }

  return base;
}

function computeSimulatedRelease(record, epsilon, seedParts = []) {
  const noisy = {};
  const adjusted = {};
  for (const field of RACE_FIELDS) {
    const value = signedNoisyCount(record[field], epsilon, [...seedParts, record.geoid, field]);
    noisy[field] = value;
    adjusted[field] = Math.max(0, value);
  }
  const simulatedPop = RACE_FIELDS.reduce((sum, field) => sum + adjusted[field], 0);
  return {
    simulatedWhite: adjusted.white,
    simulatedBlack: adjusted.black,
    simulatedAsian: adjusted.asian,
    simulatedOther: adjusted.other,
    simulatedPop,
    simulatedPopForChange: simulatedPop,
    simulatedWhiteShare: simulatedPop ? adjusted.white / simulatedPop : 0,
    simulatedChange: simulatedPop - record.truePop
  };
}

export function simulateRecordRelease(record, epsilon, seedParts = []) {
  return {
    ...record,
    ...computeSimulatedRelease(record, epsilon, seedParts)
  };
}

export function simulateRatio(numerator, denominator, epsilon, seedParts = []) {
  const noisyNumerator = noisyCount(numerator, epsilon, [...seedParts, 'numerator']);
  const noisyDenominator = Math.max(
    1,
    noisyCount(denominator, epsilon, [...seedParts, 'denominator'])
  );
  return noisyNumerator / noisyDenominator;
}

export function materializeReleaseSet(records, epsilon, seedParts = []) {
  return records.map((record) => {
    const simulated = computeSimulatedRelease(record, epsilon, seedParts);
    return {
      ...record,
      adjWhite: [simulated.simulatedWhite],
      adjBlack: [simulated.simulatedBlack],
      adjAsian: [simulated.simulatedAsian],
      adjOther: [simulated.simulatedOther],
      adjPop: [simulated.simulatedPop],
      releasedPopForChange: [simulated.simulatedPopForChange]
    };
  });
}

function upsertAggregate(target, geoid, parentGeoid) {
  let record = target.get(geoid);
  if (!record) {
    record = {
      geoid,
      parentGeoid,
      truePop: 0,
      white: 0,
      black: 0,
      asian: 0,
      other: 0,
      adjWhite: [0],
      adjBlack: [0],
      adjAsian: [0],
      adjOther: [0],
      adjPop: [0],
      releasedPopForChange: [0]
    };
    target.set(geoid, record);
  }
  return record;
}

export function aggregateBlockLevelReleases(blockTruthRecords, epsilon, seedParts = []) {
  const tractMap = new Map();
  const countyMap = new Map();

  for (const block of blockTruthRecords) {
    const simulated = computeSimulatedRelease(block, epsilon, seedParts);

    const tractRecord = upsertAggregate(tractMap, block.tractGeoid, block.countyGeoid);
    tractRecord.truePop += block.truePop;
    tractRecord.white += block.white;
    tractRecord.black += block.black;
    tractRecord.asian += block.asian;
    tractRecord.other += block.other;
    tractRecord.adjWhite[0] += simulated.simulatedWhite;
    tractRecord.adjBlack[0] += simulated.simulatedBlack;
    tractRecord.adjAsian[0] += simulated.simulatedAsian;
    tractRecord.adjOther[0] += simulated.simulatedOther;
    tractRecord.adjPop[0] += simulated.simulatedPop;
    tractRecord.releasedPopForChange[0] += simulated.simulatedPopForChange;

    const countyRecord = upsertAggregate(countyMap, block.countyGeoid, '17');
    countyRecord.truePop += block.truePop;
    countyRecord.white += block.white;
    countyRecord.black += block.black;
    countyRecord.asian += block.asian;
    countyRecord.other += block.other;
    countyRecord.adjWhite[0] += simulated.simulatedWhite;
    countyRecord.adjBlack[0] += simulated.simulatedBlack;
    countyRecord.adjAsian[0] += simulated.simulatedAsian;
    countyRecord.adjOther[0] += simulated.simulatedOther;
    countyRecord.adjPop[0] += simulated.simulatedPop;
    countyRecord.releasedPopForChange[0] += simulated.simulatedPopForChange;
  }

  return {
    tracts: Array.from(tractMap.values()).sort((left, right) => left.geoid.localeCompare(right.geoid)),
    counties: Array.from(countyMap.values()).sort((left, right) => left.geoid.localeCompare(right.geoid))
  };
}
