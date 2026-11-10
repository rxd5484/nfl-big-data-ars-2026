# The Hidden Space: Testing Tyreek Hill's Defensive Gravity

## Summary of Findings

**Dataset:** 203 Kansas City Chiefs passing plays (2021, Weeks 1-8) where both Tyreek Hill and Travis Kelce ran routes.

**High attention:** 45 plays (2+ defenders within 5 yards of Hill)  
**Low attention:** 158 plays (0-1 defenders)

---

## OUTPUT 1: Open-Space Rate

**Question:** Does Kelce get open more when Hill draws multiple defenders?

**Results:**
- High attention: **40.0%** (18/45 plays)
- Low attention: **49.4%** (78/158 plays)
- **Difference: -9.4 percentage points**

**Finding:** Kelce gets open *less* frequently when Hill has multiple nearby defenders.

---

## OUTPUT 2: Average Separation Gain

**Question:** Does Kelce gain more space during plays when Hill receives greater attention?

**Results:**
- High attention: **-1.75 yards** (n=45)
- Low attention: **-1.87 yards** (n=158)
- **Difference: +0.12 yards**

**Finding:** Both groups lose separation (defenders close in). Only 2.2% (high) and 8.9% (low) of plays show Kelce gaining space.

---

## OUTPUT 3: Defensive Attention Relationship

**Question:** Is there a statistical relationship between Hill's defensive attention and Kelce's space?

**Results:**
- Spearman correlation: **ρ = -0.078, p = 0.2711**
- High attention: 2.64 yards average
- Low attention: 3.24 yards average

**Finding:** Weak negative correlation (not statistically significant at p<0.05). More defenders near Hill slightly *reduces* Kelce's space.

---

## OUTPUT 4: Man vs Zone Coverage

**Question:** Does coverage scheme change the relationship?

**Results:**

**Man Coverage:**
- High attention: 2.01 yd (n=21)
- Low attention: 1.61 yd (n=29)

**Zone Coverage:**
- High attention: 3.27 yd (n=19)
- Low attention: 3.63 yd (n=124)

**Finding:** **Zone coverage gives Kelce ~2x more separation than man coverage, regardless of Hill's attention level.** Coverage scheme matters far more than defensive clustering around Hill.

---

## Key Takeaway

The "defensive gravity" hypothesis is not supported. **Coverage scheme (man vs. zone) is the dominant driver of Kelce's available space**, not the number of defenders near Hill. Zone coverage consistently provides more separation for Kelce whether Hill is doubled or not.

---

*Analysis by: Srikar Konakanchi*  
*GitHub: https://github.com/rxd5484/nfl-big-data-ars-2026*
