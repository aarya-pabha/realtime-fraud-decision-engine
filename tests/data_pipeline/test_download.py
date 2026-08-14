import pytest
import os
import sys
from unittest.mock import patch

# Add parent dir to path so we can import data_pipeline
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from data_pipeline.download_ieee import download_dataset

@patch('data_pipeline.download_ieee.subprocess.run')
@patch('data_pipeline.download_ieee.zipfile.ZipFile')
@patch('data_pipeline.download_ieee.os.makedirs')
def test_download_dataset(mock_makedirs, mock_zipfile, mock_run):
    # Run the function
    download_dataset(output_dir='data/raw')
    
    # Verify kaggle CLI was called
    mock_run.assert_any_call(
        ['kaggle', 'competitions', 'download', '-c', 'ieee-fraud-detection', '-p', 'data/raw'],
        check=True
    )
