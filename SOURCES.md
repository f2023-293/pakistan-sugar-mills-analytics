# Real data sources

All files in this folder contain **published, real figures** transcribed from official or industry sources.
They are used (1) for descriptive analysis and (2) to calibrate the simulated mill-level dataset in `data/synthetic/`.

| File | What it contains | Source |
|---|---|---|
| `sugar_industry_province_1997_2011.csv` | Province-wise number of mills, cane production, cane crushed, sugar produced and recovery %, 1997-98 to 2010-11 | Pakistan Bureau of Statistics, *Agricultural Statistics of Pakistan 2010-11*, Table 164 "Sugarcane and Sugar Production" (data from Pakistan Sugar Mills Association). https://www.pbs.gov.pk/sites/default/files/agriculture/publications/agricultural_statistics_of_pakistan_2010_11/tables/Table164.pdf |
| `sugarcane_area_production_province_2000_2023.csv` | Province-wise sugarcane area ('000 acres) and production ('000 tonnes), 2000-01 to 2022-23 | Crop Reporting Service, Agriculture Department Punjab, "Sugarcane Area & Production in Pakistan". https://crs-agripunjab.punjab.gov.pk/system/files/SugarCane%20Pak%20%281%29.pdf |
| `sugarcane_national_2015_2026.csv` | National sugarcane area ('000 ha) and production ('000 tonnes) | PBS Table 1 "Area and Production of Important Crops" (https://www.pbs.gov.pk/sites/default/files/tables/agriculture_statistics/new/Table_1_Area_production_crops.pdf) and Pakistan Economic Survey 2023-24, 2024-25, 2025-26 |
| `sugar_national_crushing_2015_2020.csv` | National cane crushed and sugar produced, 2015-16 to 2019-20 | Sugar Inquiry Commission Report (2020), figures supplied by provincial governments |
| `sugarcane_min_support_price_2013_2024.csv` | Official sugarcane minimum support price (Rs per 40 kg) by province | USDA FAS GAIN report "Pakistan: Sugar Annual" PK2024-0006 (data from provincial agriculture departments and PSMA) |

Notes
- Small differences between sources for the same year (e.g. 2021-22, 2022-23) are due to provisional vs revised estimates.
- KPK = Khyber Pakhtunkhwa. Balochistan has negligible sugarcane and no operating mills in these tables.
- The 2018-19 sugar production figure uses the value quoted in the Inquiry Commission narrative (5.268 Mt).
