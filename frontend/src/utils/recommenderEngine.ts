// import type { StrategyType } from '../types/strategy';

// export interface MarketSnapshot {
//   ivRank: number;          // 0–100, from metrics.iv_rank
//   daysToExpiry: number;    // from chain.days_to_expiry
//   expectedMovePct: number; // from metrics.expected_move_pct
//   spot: number;            // from chain.spot
// }

// export interface StrategyScore {
//   type: StrategyType;
//   score: number;           // 0–100
//   reasons: string[];
//   warnings: string[];
// }

// export interface RecommendationResult {
//   primary: StrategyScore;
//   alternatives: StrategyScore[];
//   rationale: string;
// }

// const STRATEGY_PROFILES: Record<StrategyType, {
//   iv_rank:    { ideal: [number, number]; weight: number };
//   dte:        { ideal: [number, number]; weight: number };
//   move_pct:   { ideal: [number, number]; weight: number };
//   risk_tier:  'conservative' | 'moderate' | 'aggressive';
// }> = {
//   iron_condor: {
//     iv_rank:    { ideal: [60, 100], weight: 35 },
//     dte:        { ideal: [15, 45],  weight: 30 },
//     move_pct:   { ideal: [0, 1.5],  weight: 25 },
//     risk_tier:  'conservative',
//   },
//   bull_put_spread: {
//     iv_rank:    { ideal: [50, 100], weight: 30 },
//     dte:        { ideal: [10, 35],  weight: 25 },
//     move_pct:   { ideal: [0, 2.0],  weight: 25 },
//     risk_tier:  'conservative',
//   },
//   long_straddle: {
//     iv_rank:    { ideal: [0, 40],   weight: 40 },
//     dte:        { ideal: [7, 30],   weight: 25 },
//     move_pct:   { ideal: [2.0, 10], weight: 25 },
//     risk_tier:  'aggressive',
//   },
//   long_strangle: {
//     iv_rank:    { ideal: [0, 45],   weight: 35 },
//     dte:        { ideal: [10, 35],  weight: 25 },
//     move_pct:   { ideal: [2.5, 10], weight: 30 },
//     risk_tier:  'aggressive',
//   },
//   bull_call_spread: {
//     iv_rank:    { ideal: [20, 70],  weight: 25 },
//     dte:        { ideal: [10, 40],  weight: 30 },
//     move_pct:   { ideal: [1.0, 4],  weight: 30 },
//     risk_tier:  'moderate',
//   },
//   bear_put_spread: {
//     iv_rank:    { ideal: [20, 70],  weight: 25 },
//     dte:        { ideal: [10, 40],  weight: 30 },
//     move_pct:   { ideal: [1.0, 4],  weight: 30 },
//     risk_tier:  'moderate',
//   },
//   bear_call_spread: {
//     iv_rank:    { ideal: [20, 70],  weight: 25 },
//     dte:        { ideal: [10, 40],  weight: 30 },
//     move_pct:   { ideal: [1.0, 4],  weight: 30 },
//     risk_tier:  'moderate',
//   },
//   covered_call: {
//     iv_rank:    { ideal: [50, 100], weight: 30 },
//     dte:        { ideal: [15, 45],  weight: 30 },
//     move_pct:   { ideal: [0, 2.5],  weight: 25 },
//     risk_tier:  'conservative',
//   },
//   custom: { // Fallback, won't really be scored
//     iv_rank:    { ideal: [0, 100], weight: 0 },
//     dte:        { ideal: [0, 100], weight: 0 },
//     move_pct:   { ideal: [0, 100], weight: 0 },
//     risk_tier:  'moderate',
//   }
// };

// function scoreSignal(value: number, ideal: [number, number]): number {
//   const [low, high] = ideal;
//   if (value >= low && value <= high) return 100;
//   const dist = Math.min(Math.max(0, low - value), Math.max(0, value - high));
//   const range = high - low || 1; // Prevent div by zero
//   return Math.max(0, 100 - (dist / range) * 100);
// }

// export function rankStrategies(
//   market: MarketSnapshot,
//   riskProfile: 'conservative' | 'moderate' | 'aggressive'
// ): StrategyScore[] {
//   const results: StrategyScore[] = [];
//   const RISK_ORDER = { conservative: 0, moderate: 1, aggressive: 2 };
//   const userRiskLevel = RISK_ORDER[riskProfile];

//   for (const [type, profile] of Object.entries(STRATEGY_PROFILES)) {
//     if (type === 'custom') continue;

//     const strategyRiskLevel = RISK_ORDER[profile.risk_tier];
//     const riskPenalty = Math.abs(strategyRiskLevel - userRiskLevel) * 15;

//     const ivScore   = scoreSignal(market.ivRank, profile.iv_rank.ideal);
//     const dteScore  = scoreSignal(market.daysToExpiry, profile.dte.ideal);
//     const moveScore = scoreSignal(market.expectedMovePct, profile.move_pct.ideal);

//     const rawScore = (
//       ivScore   * (profile.iv_rank.weight / 100) +
//       dteScore  * (profile.dte.weight / 100) +
//       moveScore * (profile.move_pct.weight / 100)
//     );

//     const finalScore = Math.max(0, Math.round(rawScore - riskPenalty));

//     const reasons: string[] = [];
//     const warnings: string[] = [];
//     if (ivScore >= 70) reasons.push(`IV Rank ${market.ivRank.toFixed(0)}/100 suits this strategy`);
//     else warnings.push(`IV Rank ${market.ivRank.toFixed(0)}/100 is not ideal`);
    
//     if (dteScore >= 70) reasons.push(`${market.daysToExpiry} DTE gives sufficient time`);
//     else if (market.daysToExpiry < 7) warnings.push(`Only ${market.daysToExpiry} DTE — gamma risk is elevated`);
    
//     if (moveScore >= 70) reasons.push(`Expected move of ${market.expectedMovePct.toFixed(1)}% aligns`);
//     else warnings.push(`Expected move ${market.expectedMovePct.toFixed(1)}% may not favour this strategy`);

//     results.push({
//       type: type as StrategyType,
//       score: finalScore,
//       reasons: reasons.slice(0, 2),
//       warnings: warnings.slice(0, 1),
//     });
//   }

//   return results.sort((a, b) => b.score - a.score);
// }

// export function getRecommendation(
//   market: MarketSnapshot,
//   riskProfile: 'conservative' | 'moderate' | 'aggressive'
// ): RecommendationResult {
//   const ranked = rankStrategies(market, riskProfile);
//   const primary = ranked[0];
//   const alternatives = ranked.slice(1, 3);

//   const rationale = `With IV Rank at ${market.ivRank.toFixed(0)}/100 and ${market.daysToExpiry} days to expiry, ${primary.reasons[0]?.toLowerCase() || 'this strategy fits current conditions'}. ${primary.warnings[0] ? `Note: ${primary.warnings[0]}.` : ''}`;

//   return { primary, alternatives, rationale };
// }

import type { StrategyType } from '../types/strategy';

export interface MarketSnapshot {
  ivRank: number;
  daysToExpiry: number;
  expectedMovePct: number;
  spot: number;
}

export interface StrategyScore {
  type: StrategyType;
  score: number;
  reasons: string[];
  warnings: string[];
}

export interface RecommendationResult {
  primary: StrategyScore;
  alternatives: StrategyScore[];
  rationale: string;
}

const STRATEGY_PROFILES: Record<StrategyType, {
  iv_rank:    { ideal: [number, number]; weight: number };
  dte:        { ideal: [number, number]; weight: number };
  move_pct:   { ideal: [number, number]; weight: number };
  risk_tier:  'conservative' | 'moderate' | 'aggressive';
}> = {
  iron_condor: { iv_rank: { ideal: [60, 100], weight: 35 }, dte: { ideal: [15, 45], weight: 30 }, move_pct: { ideal: [0, 1.5], weight: 25 }, risk_tier: 'conservative' },
  bull_put_spread: { iv_rank: { ideal: [50, 100], weight: 30 }, dte: { ideal: [10, 35], weight: 25 }, move_pct: { ideal: [0, 2.0], weight: 25 }, risk_tier: 'conservative' },
  long_straddle: { iv_rank: { ideal: [0, 40], weight: 40 }, dte: { ideal: [7, 30], weight: 25 }, move_pct: { ideal: [2.0, 10], weight: 25 }, risk_tier: 'aggressive' },
  long_strangle: { iv_rank: { ideal: [0, 45], weight: 35 }, dte: { ideal: [10, 35], weight: 25 }, move_pct: { ideal: [2.5, 10], weight: 30 }, risk_tier: 'aggressive' },
  bull_call_spread: { iv_rank: { ideal: [20, 70], weight: 25 }, dte: { ideal: [10, 40], weight: 30 }, move_pct: { ideal: [1.0, 4], weight: 30 }, risk_tier: 'moderate' },
  bear_put_spread: { iv_rank: { ideal: [20, 70], weight: 25 }, dte: { ideal: [10, 40], weight: 30 }, move_pct: { ideal: [1.0, 4], weight: 30 }, risk_tier: 'moderate' },
  bear_call_spread: { iv_rank: { ideal: [20, 70], weight: 25 }, dte: { ideal: [10, 40], weight: 30 }, move_pct: { ideal: [1.0, 4], weight: 30 }, risk_tier: 'moderate' },
  covered_call: { iv_rank: { ideal: [50, 100], weight: 30 }, dte: { ideal: [15, 45], weight: 30 }, move_pct: { ideal: [0, 2.5], weight: 25 }, risk_tier: 'conservative' },
  custom: { iv_rank: { ideal: [0, 100], weight: 0 }, dte: { ideal: [0, 100], weight: 0 }, move_pct: { ideal: [0, 100], weight: 0 }, risk_tier: 'moderate' }
};

function scoreSignal(value: number, ideal: [number, number]): number {
  const [low, high] = ideal;
  if (value >= low && value <= high) return 100;
  const dist = Math.min(Math.max(0, low - value), Math.max(0, value - high));
  const range = high - low || 1; 
  return Math.max(0, 100 - (dist / range) * 100);
}

export function rankStrategies(market: MarketSnapshot, riskProfile: 'conservative' | 'moderate' | 'aggressive'): StrategyScore[] {
  const results: StrategyScore[] = [];
  const RISK_ORDER = { conservative: 0, moderate: 1, aggressive: 2 };
  const userRiskLevel = RISK_ORDER[riskProfile];

  for (const [type, profile] of Object.entries(STRATEGY_PROFILES)) {
    if (type === 'custom') continue;
    const strategyRiskLevel = RISK_ORDER[profile.risk_tier];
    const riskPenalty = Math.abs(strategyRiskLevel - userRiskLevel) * 15;

    const ivScore = scoreSignal(market.ivRank, profile.iv_rank.ideal);
    const dteScore = scoreSignal(market.daysToExpiry, profile.dte.ideal);
    const moveScore = scoreSignal(market.expectedMovePct, profile.move_pct.ideal);

    const rawScore = (ivScore * (profile.iv_rank.weight / 100) + dteScore * (profile.dte.weight / 100) + moveScore * (profile.move_pct.weight / 100));
    const finalScore = Math.max(0, Math.round(rawScore - riskPenalty));

    const reasons: string[] = [];
    const warnings: string[] = [];
    if (ivScore >= 70) reasons.push(`IV Rank ${market.ivRank.toFixed(0)}/100 suits this strategy`);
    else warnings.push(`IV Rank ${market.ivRank.toFixed(0)}/100 is not ideal`);
    
    if (dteScore >= 70) reasons.push(`${market.daysToExpiry} DTE gives sufficient time`);
    else if (market.daysToExpiry < 7) warnings.push(`Only ${market.daysToExpiry} DTE — gamma risk is elevated`);
    
    if (moveScore >= 70) reasons.push(`Expected move of ${market.expectedMovePct.toFixed(1)}% aligns`);
    else warnings.push(`Expected move ${market.expectedMovePct.toFixed(1)}% may not favour this strategy`);

    results.push({
      type: type as StrategyType,
      score: finalScore,
      reasons: reasons.slice(0, 2),
      warnings: warnings.slice(0, 1),
    });
  }
  return results.sort((a, b) => b.score - a.score);
}

export function getRecommendation(market: MarketSnapshot, riskProfile: 'conservative' | 'moderate' | 'aggressive'): RecommendationResult {
  const ranked = rankStrategies(market, riskProfile);
  const primary = ranked[0];
  const alternatives = ranked.slice(1, 3);
  const rationale = `With IV Rank at ${market.ivRank.toFixed(0)}/100 and ${market.daysToExpiry} days to expiry, ${primary.reasons[0]?.toLowerCase() || 'this strategy fits current conditions'}. ${primary.warnings[0] ? `Note: ${primary.warnings[0]}.` : ''}`;
  return { primary, alternatives, rationale };
}