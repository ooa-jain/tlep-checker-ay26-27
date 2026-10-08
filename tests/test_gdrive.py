"""
Test Google Drive Link Extraction and Integration Engine
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.google_drive import extract_folder_id_from_url, GoogleDriveConnector


def main():
    test_urls = [
        ("https://drive.google.com/drive/folders/1bCz8_X9QpLkM_xyz1234567890abcdef", "1bCz8_X9QpLkM_xyz1234567890abcdef"),
        ("https://drive.google.com/drive/u/1/folders/1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O", "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O"),
        ("https://drive.google.com/folderview?id=abcdefghijklmnopqrstuvwxyz123", "abcdefghijklmnopqrstuvwxyz123"),
        ("1234567890123456789012345678", "1234567890123456789012345678")
    ]
    
    for url, expected_id in test_urls:
        extracted = extract_folder_id_from_url(url)
        assert extracted == expected_id, f"Extraction failed for {url}: got {extracted}, expected {expected_id}"
        print(f"Extracted folder ID from '{url[:40]}...': {extracted}")

    # Test invalid url
    assert extract_folder_id_from_url("https://invalid-link.com") is None
    print("Invalid URL correctly rejected.")
    
    # Test connector initialization without auth throws clean PermissionError
    connector = GoogleDriveConnector()
    try:
        connector.list_folder_files("dummy_folder")
        assert False, "Should have raised PermissionError"
    except PermissionError as pe:
        print(f"Clean permission error caught as expected: {pe}")
        
    print("All Google Drive unit tests passed!")


if __name__ == "__main__":
    main()
