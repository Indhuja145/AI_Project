# Real data import

The app loads `data/reviews.json` and `data/products.json` automatically when they exist. The raw Amazon file is intentionally not committed to source control.

From the project root, run:

```powershell
python backend/import_amazon.py --download
```

This downloads the official Amazon Fashion 5-core subset from the UCSD/Julian McAuley source, maps `reviewText` → `review_text`, `overall` → `rating`, `asin` → `product_id`, and `reviewTime` → `review_date`, then runs the local ABSA, emotion, complaint, seasonal, and fake-review pipeline.

For a Kaggle CSV, run:

```powershell
python backend/import_amazon.py --source data/your-kaggle-file.csv
```
