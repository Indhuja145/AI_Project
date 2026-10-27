"""Download the Kaggle fashion review dataset and show its local files."""
from pathlib import Path
import shutil
import kagglehub

path = Path(kagglehub.dataset_download('thedevastator/fashion-products-on-amazon-ratings-prices-and-pa'))
print(f'Path to dataset files: {path}')
for item in path.rglob('*'):
    if item.is_file():
        print(item)
        destination = Path(__file__).resolve().parent.parent / 'data' / item.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        print(f'Copied to project: {destination}')
