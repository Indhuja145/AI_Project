from pathlib import Path
import shutil
import zipfile
import kagglehub

source=Path(kagglehub.dataset_download('hiteshsuthar101/myntra-fashion-product-dataset', path='Fashion Dataset.csv'))
print(f'Path to dataset files: {source}')
destination=Path(__file__).resolve().parent.parent/'data'/'myntra_fashion_products.csv'
destination.parent.mkdir(parents=True,exist_ok=True)
if zipfile.is_zipfile(source):
    with zipfile.ZipFile(source) as archive:
        csv_name=next(name for name in archive.namelist() if name.lower().endswith('.csv'))
        destination.write_bytes(archive.read(csv_name))
else:
    shutil.copy2(source,destination)
print(f'Copied: {destination}')
