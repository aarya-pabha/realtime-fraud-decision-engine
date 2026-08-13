import pytest
import os
import sys

# Add parent dir to path so we can import data_pipeline
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from data_pipeline.download_ieee import download_dataset

def test_download_dataset_calls_kaggle_and_unzips(mocker):
    # Mock subprocess.run and zipfile using Context7 pytest-mock standard
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value.returncode = 0
    
    mocker.patch('zipfile.ZipFile')
    
    # Run the function
    download_dataset(output_dir='data/raw')
    
    # Verify kaggle CLI was called
    mock_run.assert_any_call(
        ['kaggle', 'competitions', 'download', '-c', 'ieee-fraud-detection', '-p', 'data/raw'],
        check=True
    )
