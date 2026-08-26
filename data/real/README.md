# Real Public Data Sources

This directory contains small samples of real public/open data used alongside synthetic demo data to demonstrate that SkillSetu's architecture supports real sources.

## Sources Used

### 1. NSDC Qualification Packs
- **What**: Skill names, NSQF levels, sector mappings
- **Source**: https://nsdcindia.org/nos-qp
- **License**: Public government data
- **Date accessed**: August 2026
- **Used in**: `data/demo/skills.json` — entries with `"source": "NSDC_PUBLIC"`

### 2. Maharashtra District List
- **What**: Official 36-district list with region groupings
- **Source**: https://maharashtra.gov.in
- **License**: Public government data
- **Used in**: District names and groupings across all demo datasets

### 3. NCO-2015 Occupation Codes
- **What**: National Classification of Occupations codes
- **Source**: https://labour.gov.in/nco-2015
- **License**: Public government data
- **Used in**: Job title taxonomy mapping in `data/demo/jobs.json`

## How to Refresh

To update real data samples:
1. Download latest from the source URLs above
2. Extract relevant fields into the corresponding demo JSON files
3. Mark entries with `"source": "PUBLIC_<SOURCE_NAME>"`
4. Update the "Date accessed" above

## Note

The MVP demo is **not dependent** on these real sources. All demo functionality works with the synthetic data alone. Real data samples exist purely to demonstrate architectural readiness.
