from pathlib import Path
import zipfile

source=Path(__file__).resolve().parent.parent/'data'/'myntra_fashion_products.csv'
if not zipfile.is_zipfile(source):
    raise SystemExit(f'Not a ZIP-wrapped Kaggle file: {source}')
with zipfile.ZipFile(source) as archive:
    csv_name=next(name for name in archive.namelist() if name.lower().endswith('.csv'))
    source.write_bytes(archive.read(csv_name))
print(f'Extracted {csv_name} to {source}')
