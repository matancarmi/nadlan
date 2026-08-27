import { MortgageTranche } from "./types";

// Mirrors backend/app/services/finance.py exactly - keep both in sync.
// This lets the per-card mortgage widget recompute instantly as the user
// tweaks equity/term, without a round trip to the server.

export function monthlyPaymentForTranche(principal: number, annualRatePct: number, termYears: number): number {
  if (principal <= 0) return 0;
  const monthlyRate = annualRatePct / 100 / 12;
  const n = termYears * 12;
  if (monthlyRate === 0) return principal / n;
  const factor = Math.pow(1 + monthlyRate, n);
  return (principal * monthlyRate * factor) / (factor - 1);
}

export function calculateMortgage(
  askingPrice: number,
  equityNis: number,
  loanTermYears: number,
  mix: MortgageTranche[]
) {
  const loanAmount = Math.max(askingPrice - equityNis, 0);
  let totalMonthlyPayment = 0;
  for (const tranche of mix) {
    const tranchePrincipal = loanAmount * (tranche.share_pct / 100);
    totalMonthlyPayment += monthlyPaymentForTranche(tranchePrincipal, tranche.annual_rate_pct, loanTermYears);
  }
  return {
    loanAmount: Math.round(loanAmount),
    equityUsed: Math.round(Math.min(equityNis, askingPrice)),
    monthlyPayment: Math.round(totalMonthlyPayment),
  };
}
