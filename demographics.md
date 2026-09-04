# Participant Demographics

Source: `Data/*/participant_info.json` (26 session folders; each participant ran one 10-bit and one 8-bit session). Generated 26 Jun 2026.

## Summary

- **Session folders:** 26
- **Unique participants:** 13

Statistics below are per unique participant (n=13, all participants included).

| Measure | Value (n=13) |
|---|---|
| Age — mean (SD) | 24.2 (4.3) |
| Age — median [range] | 23 [21–38] |
| Sex — M / F / O | 10 / 2 / 1 |
| Ocular dominance — Right / Left | 12 / 1 |
| Education level | Undergrad 5, Other 5, PhD 2, Master 1 |

### Sex
- Male: 10 (77%)
- Female: 2 (15%)
- Other: 1 (8%)

### Ocular dominance
- OD / Right: 12 (92%)
- OS / Left: 1 (8%)

### Education level
- Undergraduate: 5
- Other: 5
- PhD: 2
- Master: 1

## Per-participant table

| ID | Age | Sex | Ocular dominance | Level | Year | Experimenter |
|---|---|---|---|---|---|---|
| AB | 22 | M | OD (Right) | Undergraduate | 4 | Oliver Kairaitis |
| AS | 21 | F | OD (Right) | Undergraduate | 4 | Oliver Kairaitis |
| Bhuvan | 24 | M | OD (Right) | Master | 2 | Mo |
| CH | 22 | M | OD (Right) | Other / Undergraduate ¹ | 1 | Oliver Kairaitis |
| DS | 23 | M | OD (Right) | Other | 1 | Oliver Kairaitis |
| EH | 22 | M | OD (Right) | Other | 1 | Oliver Kairaitis |
| FF | 24 | M | OD (Right) | Undergraduate | 1 | Oliver Kairaitis |
| FG | 23 | M | OS (Left) / OD (Right) ¹ | Other / Undergraduate ¹ | 1 | Oliver Kairaitis |
| KN | 21 | F | OD (Right) | Undergraduate | 1 | Oliver Kairaitis |
| Mo | 38 | O / M ¹ | OD (Right) | PhD | 1 / 4 ¹ | Mo |
| OK2 | 23 | M | OD (Right) | Other | 1 | Oliver Kairaitis |
| OM | 23 | M | OD (Right) | Undergraduate | 4 | Oliver Kairaitis |
| PRtest | 28 | M | OD (Right) | PhD | 4 | Unknown |

¹ Field differs between the participant's 10-bit and 8-bit session files (10-bit value listed first).

## Inconsistencies between sessions

The same participant's two session files disagree on a few self-report fields:

- **CH** — level: `Other` (10-bit) vs `Undergraduate` (8-bit)
- **FG** — ocular dominance: `OS (Left)` (10-bit) vs `OD (Right)` (8-bit); level: `Other` vs `Undergraduate`
- **Mo** — sex: `O` (10-bit) vs `M` (8-bit); year: `1` vs `4`

These likely reflect data-entry variation at session start and should be reconciled against the recruitment records before final reporting.