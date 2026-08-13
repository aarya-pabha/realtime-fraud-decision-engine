import subprocess
import os
import zipfile
from dotenv import load_dotenv

load_dotenv() # Load Kaggle keys from .env file

def download_dataset(output_dir: str = 'data/raw'):
    """Downloads the IEEE-CIS dataset via Kaggle API and extracts it."""
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Downloading IEEE dataset to {output_dir}...")
    try:
        subprocess.run(
            ['kaggle', 'competitions', 'download', '-c', 'ieee-fraud-detection', '-p', output_dir],
            check=True
        )
    except FileNotFoundError:
        raise RuntimeError("Kaggle CLI not found. Please install kaggle and set up ~/.kaggle/kaggle.json")
    
    zip_path = os.path.join(output_dir, 'ieee-fraud-detection.zip')
    if os.path.exists(zip_path):
        print(f"Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print("Extraction complete.")

if __name__ == "__main__":
    download_dataset()
