# The Hidden Space: Does Tyreek Hill's Defensive Attention Help Travis Kelce Get Open?

**NFL Big Data Bowl 2026 Project**  
**Team:** Srikar Konakanchi  
**Dataset:** 2021 Kansas City Chiefs (Weeks 1–8, 203 passing plays)

---

## Research Question

When defenses send multiple defenders to cover Tyreek Hill, does Travis Kelce get more open space to operate? We use player tracking data to measure defensive attention around Hill and its relationship to Kelce's separation from coverage defenders.

---

## Answer

**No.** Kelce does not get more space when Hill draws multiple defenders. In fact, he gets slightly *less* space.

But we found something more important: **coverage scheme (man vs. zone) is what actually creates or eliminates space for Kelce**, regardless of how many defenders are near Hill.

---

## Three Core Metrics

### Metric 1: Defensive Attention Around Hill
**What we measured:** Number of coverage defenders within 5 yards of Hill at 1.5 seconds after the snap.

**Key findings:**
- 76% of plays: Hill has 0-1 nearby defenders (low attention)
- 24% of plays: Hill has 2+ nearby defenders (high attention)
- Most common scenario: exactly 1 defender near Hill (140/236 plays)

**What this means:** Defenses rarely send multiple coverage defenders to shadow Hill. When they do, it's usually in man coverage schemes.

---

### Metric 2: Kelce's Separation Over Time
**What we measured:** Distance from Kelce to his nearest coverage defender, tracked from snap through 3 seconds.

**Key findings:**
- At snap: 4.95 yards average separation
- At 1.5s: 3.10 yards average separation  
- **Kelce loses 1.85 yards on average** as defenders converge
- Only 7.4% of plays show Kelce gaining separation

**What this means:** The passing window closes fast. Kelce starts with decent space but defenders close in quickly. Mahomes needs to throw early to exploit initial separation.

---

### Metric 3: Relationship Between Hill Attention and Kelce Space
**What we measured:** Statistical correlation between the number of defenders near Hill and Kelce's available separation.

**Key findings:**
- High Hill attention: Kelce averages **2.64 yards** separation
- Low Hill attention: Kelce averages **3.24 yards** separation
- Spearman correlation: ρ = −0.078, p = 0.27 (not significant)

**What this means:** More defenders near Hill is associated with *less* space for Kelce, not more. The relationship is weak and not statistically significant.

---

## Four Analysis Outputs

### Output 1: Open-Space Rate
**Question:** Does Kelce get open (≥3 yards separation) more frequently when Hill draws attention?

**Answer:** No.
- High Hill attention: **40.0%** of plays (18/45)
- Low Hill attention: **49.4%** of plays (78/158)
- **Difference: −9.4 percentage points**

Kelce is actually *less* likely to be open when Hill has multiple nearby defenders.

---

### Output 2: Average Separation Gain
**Question:** Does Kelce gain more space during plays when Hill receives greater attention?

**Answer:** No. Both groups lose separation.
- High Hill attention: **−1.75 yards** average gain
- Low Hill attention: **−1.87 yards** average gain
- **Difference: +0.12 yards** (negligible)

Defenders close in on Kelce regardless of Hill's situation. Only 2-9% of plays show positive separation gain.

---

### Output 3: Defensive Attention Relationship
**Question:** Is there a measurable statistical relationship?

**Answer:** Weak negative correlation, not statistically significant.
- Correlation: ρ = −0.078, p = 0.27
- More defenders near Hill → slightly less space for Kelce
- Relationship is too weak to be reliable

---

### Output 4: Man vs Zone Coverage — The Real Story
**Question:** Does coverage scheme change the pattern?

**Answer:** Coverage scheme IS the pattern.

#### Man Coverage
- High Hill attention: 2.01 yards
- Low Hill attention: 1.61 yards
- **Always tight coverage on Kelce**

#### Zone Coverage
- High Hill attention: 3.27 yards
- Low Hill attention: 3.63 yards
- **Always loose coverage on Kelce**

**Zone coverage gives Kelce 2x more separation than man coverage**, regardless of Hill's defensive attention level.

Within each scheme, Hill's attention has minimal effect:
- Man: +0.40 yards difference (high vs low)
- Zone: −0.36 yards difference (high vs low)

---

## Key Takeaway

### The "defensive gravity" hypothesis is not supported by the data.

**What we expected:**  
Hill draws defenders → Kelce gets more space

**What we found:**  
Coverage scheme determines Kelce's space, not Hill's attention

**Why this matters:**
1. **For coaches:** Focus on forcing zone coverage, not just creating double-teams on your star receiver
2. **For scouts:** Tight end separation depends more on defensive scheme than receiver gravity
3. **For broadcasters:** "When defenses play zone, Kelce finds 3-4 yards of space. In man coverage, that window shrinks to under 2 yards — regardless of what's happening around Tyreek Hill."

---

## Why the Hypothesis Failed

### Possible explanations:

1. **Scheme drives attention, not vice versa**  
   When defenses play man coverage, they naturally put more defenders near both Hill AND Kelce. High attention around Hill doesn't *create* tight coverage on Kelce — they're both consequences of choosing man coverage.

2. **Defenses are coordinated**  
   When defenses send 2+ defenders to Hill, they're running aggressive schemes that compress space everywhere, not just around Hill.

3. **The Chiefs exploit zone, not gravity**  
   Mahomes and Andy Reid's offense may be designed to beat zone coverage with route concepts, not to exploit individual matchups through gravity.

4. **Sample composition**  
   High-attention plays (n=45) often occur in high-leverage situations (3rd down, red zone) where defenses are more aggressive across the board.

---

## Methods Summary

### Data
- 2021 NFL tracking data (10 frames per second)
- Kansas City Chiefs offensive plays, Weeks 1–8
- Filtered to plays where both Hill and Kelce ran routes
- Final sample: 203 plays

### Analysis
- **Metric 1:** Euclidean distance calculations, defender-count classification
- **Metric 2:** Frame-by-frame separation tracking, bootstrap confidence intervals
- **Metric 3:** Spearman correlation, Mann-Whitney U tests, OLS regression
- All measurements use coverage defenders only (excludes pass rushers)
- Coordinates normalized so offense always moves left-to-right

### Statistical Tests
- Bootstrap 95% confidence intervals (10,000 resamples)
- Mann-Whitney U (non-parametric group comparisons)
- Spearman rank correlation (non-linear relationships)
- OLS regression controlling for coverage type

---

## Limitations

1. **Proximity ≠ Assignment:** We measured defenders *near* Hill, but cannot confirm they were assigned to cover him
2. **Separation ≠ Open:** A receiver can have 3 yards of space but still be covered (wrong leverage, blocked throwing lane)
3. **Observational data:** Cannot prove causation — only associations
4. **Small subgroups:** High-attention plays in specific coverage types (n=19-21) limit statistical power
5. **Single team, single season:** Results reflect 2021 Chiefs' scheme and may not generalize

---

## Files and Reproducibility

### Code
- `src/metric1_defensive_attention.py` — Calculate Hill's defensive attention
- `src/metric2_kelce_separation.py` — Track Kelce's separation over time
- `src/metric3_gravity_space_relationship.py` — Test the gravity-space relationship
- `src/final_outputs_analysis.py` — Merge metrics and produce 4 outputs
- `src/visualize_metrics.py` — Generate metric visualizations

### Data
- `data/processed/metric1_attention.csv` — Defender counts around Hill
- `data/processed/metric2_separation_gain.csv` — Kelce's separation changes
- `data/processed/metric3_gravity_space.csv` — Combined metric for analysis
- `data/processed/final_analysis.csv` — Merged dataset (203 plays)

### Outputs
- 7 publication-ready visualizations (300 DPI PNG)
- Complete findings report
- All results reproducible by running the Python scripts

### GitHub
Repository: https://github.com/rxd5484/nfl-big-data-ars-2026  
Branch: `Data+Metrics`

---

## Conclusion

We set out to test whether Tyreek Hill's defensive gravity creates hidden space for Travis Kelce. The answer is no — but we discovered something more actionable: **coverage scheme is the dominant driver of tight end separation in the Chiefs' offense.**

Zone coverage consistently gives Kelce 2x more space than man coverage, and this relationship holds regardless of how many defenders are near Hill. For teams trying to replicate Kansas City's success, the lesson is clear: design plays that force zone coverage, not just plays that draw double-teams.

This finding is data-driven, statistically validated, and immediately useful for coaches, scouts, and analysts trying to understand what makes the Chiefs' passing attack so effective.

---

*Analysis completed November 2024*  
*NFL Big Data Bowl 2026*
