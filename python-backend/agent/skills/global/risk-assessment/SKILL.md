---
name: risk-assessment
description: Portfolio risk assessment and position sizing framework
category: risk
---

# Risk Assessment Skill

## Workflow
1. **Portfolio snapshot**: Current positions, exposure, unrealized P&L
2. **Correlation check**: New trade correlation with existing positions
3. **Position sizing**: Based on account risk (max 1-2% per trade)
4. **Drawdown check**: Current drawdown vs maximum allowed (typically 10-20%)
5. **Concentration check**: No single asset > 20% of portfolio

## Risk Rules
- Max loss per trade: 1% of account for conservative, 2% for aggressive
- Max correlated exposure: 5% (e.g., multiple USD pairs)
- Stop placement: Technical level + spread + slippage buffer
- Scale-in rules: Only add to winning positions, never to losers
- Daily loss limit: 3% — stop trading for the day if hit

## Output Format
Provide: Risk score (1-10), Position size, Stop loss level, Risk/reward ratio, Approval (yes/no/modify)
