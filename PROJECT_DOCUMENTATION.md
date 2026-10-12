# RepoTrust documentation

## Scoring (start at 100, bucketed to the nearest 10 below)
archived -50 (always AVOID), disabled -50, fork -5, no license -10, idle >730d -40 / >365d -30 / >180d -15 / >90d -5, created <30d -15 / <90d -5, stars <10 -10 / <100 -5, open issues >=500 -10 / >=100 -5.
Verdict: 70+ SAFE, 40-60 CAUTION, below 40 AVOID.

## Write methods (all return "OK:..." or "ERR:...", none revert on user mistakes)
`review(repo)` payable, `deposit()` payable, `withdraw(amount)` (0 = all), `withdraw_fees()` owner, `set_review_fee(fee)` owner.

## Views
`get_review`, `get_history`, `get_repos(offset, limit)`, `get_stats`, `get_balance_of`, `get_last_result`, `get_config`.
