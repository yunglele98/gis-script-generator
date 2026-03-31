# Kensington Market Field Study Guide

**Duration:** 1 week
**Teams:** 3 teams of 2 (6 people)
**Area:** Kensington Market, Toronto

## Before Going Out (Day 1 Morning)

- Download offline map areas in Field Maps for each team's phone
- Print a paper backup of the zone map with morphological zones — phones die
- Test Survey123 forms end-to-end with one dummy submission per form, then delete it
- Set up a shared WhatsApp/Signal group for live coordination between teams

## Daily Routine

- **Morning briefing (15 min):** assign zones, set daily targets (e.g., "Team 2 finishes Augusta Ave today")
- **Teams work 10am–4pm** with a lunch overlap at the market to debrief
- **Evening sync (30 min):** run the PostGIS sync script, review the day's submissions, flag issues

```bash
# Evening sync command
python -m field_survey.sync_field_data \
    --config field_survey/sync_config.json \
    --agol-token $(cat C:/Users/liam1/token.txt)
```

## Coverage Strategy

- **Day 1–2:** Commercial corridors first (Kensington Ave, Augusta Ave, Baldwin St) — businesses close early, weekday hours matter
- **Day 3–4:** Residential streets (Bellevue, Oxford, Nassau, Lippincott)
- **Day 5:** Fill gaps, revisit problem addresses, catch businesses that were closed
- **Weekday vs weekend:** storefronts are easier on weekdays (owners present), residents are easier on weekends (home)

## Morphological Zones

| Zone | Buildings | Commercial |
|------|-----------|------------|
| Axe central du marché | 234 | 232 |
| Artère périphérique commerciale | 214 | 184 |
| Rue secondaire du marché | 171 | 96 |
| Intérieur résidentiel victorien | 393 | 28 |
| Ruelle / Cottage ouvrier | 40 | 2 |
| Nœud institutionnel / résidentiel | 10 | 1 |

## Practical Tips

- Bring portable battery packs — GPS + camera drains phones fast
- Clipboard with consent forms in paper as backup
- Dress for walking 15–20 km/day
- Kensington gets busy after 11am on weekends — plan around that
- Some business owners speak Portuguese, Mandarin, or Vietnamese — note language barriers for follow-up

## Data Quality

- Run the sync script every evening to catch submission errors early
- Check the web map daily for spatial gaps (zoom out, look for empty blocks)
- Export a daily CSV backup from AGOL as insurance

## Tools

| Tool | Purpose |
|------|---------|
| ArcGIS Field Maps | Map navigation, building assessment, tap-to-survey |
| Survey123 | Resident, business, intercept, student, contact surveys |
| Mapillary (optional) | Street-level photo capture while walking |
| PostGIS sync script | Nightly data sync to local database |

## Key URLs

- **Web map:** https://www.arcgis.com/apps/mapviewer/index.html?webmap=597d45ca0eda44abbe8806c7736be0bf
- **Feature service:** https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer

## After the Week

- Run a final full sync to PostGIS
- Generate a coverage report: % of buildings assessed, surveys completed per zone
- Export final datasets for analysis
