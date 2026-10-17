# fuelprices-gr-json

Daily Greek fuel prices per prefecture as a small JSON file, for the ESP32 Weather & Tank
station (and anything else that cannot read PDF files).

The Ministry of Development publishes the prices every working day as a PDF at
[www.fuelprices.gr](https://www.fuelprices.gr) (prices of the previous day). A GitHub
Actions workflow runs `convert.py` a few times a day, Monday to Saturday, and commits
`prices.json` when a new bulletin appears.

## The JSON file

```json
{
  "date": "2026-10-15",
  "previous": "2026-10-14",
  "source": "www.fuelprices.gr",
  "prefectures": {
    "ATTICA": { "name": "ΑΤΤΙΚΗΣ", "u95": 2.181, "u100": 2.454, "diesel": 2.099,
                "lpg": 1.122, "heating": 1.526,
                "chg": { "u95": -0.002, "u100": -0.003, "diesel": 0.004, "lpg": 0.011 } },
    ...
  }
}
```

Prices in €/L including VAT. `chg` = change since the previous bulletin.
`heating` (heating diesel) exists only from 15 October to 30 April; a price is left out
when the bulletin shows "-".

Read it from: `https://raw.githubusercontent.com/<user>/fuelprices-gr-json/main/prices.json`

## Setup on GitHub (once)

1. On github.com: **New repository**, name `fuelprices-gr-json`, **Public**, no README.
2. Upload the contents of this folder (`convert.py`, `prices.json`, `README.md`, `LICENSE`,
   `.gitignore` and the `.github` folder). With git:
   ```bash
   git init -b main
   git add .
   git commit -m "Fuel price converter"
   git remote add origin https://github.com/<user>/fuelprices-gr-json.git
   git push -u origin main
   ```
3. Repository **Settings → Actions → General → Workflow permissions**: choose
   **Read and write permissions** and Save (the workflow commits `prices.json`).
4. **Actions** tab → **Update fuel prices** → **Run workflow** once to test it.

GitHub pauses scheduled workflows of a repository that has had no activity for 60 days;
the daily commits of `prices.json` count as activity, so it keeps running.

## Run locally

```bash
pip install pypdf
python convert.py prices.json
```

Prefecture list and idea from [mavroprovato/fuelpricesgr](https://github.com/mavroprovato/fuelpricesgr)
(MIT License).
