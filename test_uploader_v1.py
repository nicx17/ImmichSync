import os
import tempfile
import json
import pytest
from unittest.mock import patch, mock_open
import requests

# Set environment variables BEFORE importing the module to mock the constants
os.environ["SCREENSHOTS_PATH"] = "/tmp/mock_screenshots"
os.environ["IMMICH_API_KEY"] = "mock_api_key"
os.environ["IMMICH_LOCAL_URL"] = "http://localhost:2283"
os.environ["IMMICH_EXTERNAL_URL"] = "https://immich.example.com"
os.environ["IMMICH_ALBUM_NAME"] = "Test Album"

# Import the module under test
import uploader_v1


@pytest.fixture
def mock_env(monkeypatch):
    """Ensure environment variables are consistently mocked for all tests."""
    monkeypatch.setattr(uploader_v1, "LOCAL_URL", "http://localhost:2283")
    monkeypatch.setattr(uploader_v1, "EXTERNAL_URL", "https://immich.example.com")
    monkeypatch.setattr(uploader_v1, "API_KEY", "mock_api_key")
    monkeypatch.setattr(uploader_v1, "ALBUM_NAME", "Test Album")
    monkeypatch.setattr(uploader_v1, "SCREENSHOTS_FOLDER", "/tmp/mock_screenshots")


def test_get_active_url_local_success(requests_mock, mock_env):
    """Test get_active_url when local URL is accessible."""
    requests_mock.get("http://localhost:2283/api/server/ping", status_code=200)
    url = uploader_v1.get_active_url()
    assert url == "http://localhost:2283"


def test_get_active_url_local_fails_external_success(requests_mock, mock_env):
    """Test get_active_url when local fails and fallback to external."""
    requests_mock.get("http://localhost:2283/api/server/ping", status_code=500)
    # The code doesn't ping external, it just returns it if local fails
    url = uploader_v1.get_active_url()
    assert url == "https://immich.example.com"


def test_get_active_url_fails_both(monkeypatch, requests_mock):
    """Test get_active_url when neither local nor external are configured correctly."""
    monkeypatch.setattr(uploader_v1, "LOCAL_URL", None)
    monkeypatch.setattr(uploader_v1, "EXTERNAL_URL", None)
    url = uploader_v1.get_active_url()
    assert url is None


def test_get_album_id_success(requests_mock):
    """Test getting an album ID successfully."""
    mock_response = [
        {"albumName": "Other Album", "id": "123"},
        {"albumName": "Test Album", "id": "456"},
    ]
    requests_mock.get("http://mock_url/api/albums", json=mock_response, status_code=200)
    album_id = uploader_v1.get_album_id("http://mock_url", "api_key", "Test Album")
    assert album_id == "456"


def test_get_album_id_not_found(requests_mock):
    """Test getting an album ID when the name is not in the list."""
    mock_response = [{"albumName": "Other Album", "id": "123"}]
    requests_mock.get("http://mock_url/api/albums", json=mock_response, status_code=200)
    album_id = uploader_v1.get_album_id("http://mock_url", "api_key", "Test Album")
    assert album_id is None


def test_get_album_id_error(requests_mock):
    """Test getting an album ID when the API returns an error."""
    requests_mock.get("http://mock_url/api/albums", status_code=500)
    album_id = uploader_v1.get_album_id("http://mock_url", "api_key", "Test Album")
    assert album_id is None


def test_add_to_album_success(requests_mock):
    """Test adding an asset to an album successfully."""
    requests_mock.put(
        "http://mock_url/api/albums/album_123/assets",
        json=[{"id": "asset_456"}],
        status_code=200,
    )
    result = uploader_v1.add_to_album(
        "http://mock_url", "api_key", "album_123", "asset_456"
    )
    assert result is True


def test_add_to_album_failure(requests_mock):
    """Test failure when adding an asset to an album."""
    requests_mock.put("http://mock_url/api/albums/album_123/assets", status_code=400)
    result = uploader_v1.add_to_album(
        "http://mock_url", "api_key", "album_123", "asset_456"
    )
    assert result is False


@patch("os.path.isfile", return_value=True)
@patch("os.stat")
@patch("builtins.open", new_callable=mock_open, read_data=b"mock data")
@patch("requests.post")
def test_upload_asset_created(mock_post, mock_file, mock_stat, mock_isfile):
    """Test successful new upload (201 Created)."""
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1600000000
    mock_stat.return_value.st_ctime = 1600000000

    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"id": "new_asset_id"}

    asset_id = uploader_v1.upload_asset(
        "/fake/path/image.jpg", "http://mock_url", "api_key"
    )
    assert asset_id == "new_asset_id"


@patch("os.path.isfile", return_value=True)
@patch("os.stat")
@patch("builtins.open", new_callable=mock_open, read_data=b"mock data")
@patch("requests.post")
def test_upload_asset_soft_duplicate(mock_post, mock_file, mock_stat, mock_isfile):
    """Test soft duplicate upload (200 OK)."""
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1600000000
    mock_stat.return_value.st_ctime = 1600000000

    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "existing_asset_id"}

    asset_id = uploader_v1.upload_asset(
        "/fake/path/image.jpg", "http://mock_url", "api_key"
    )
    assert asset_id == "existing_asset_id"


@patch("os.path.isfile", return_value=True)
@patch("os.stat")
@patch("builtins.open", new_callable=mock_open, read_data=b"mock data")
@patch("requests.post")
def test_upload_asset_hard_duplicate(mock_post, mock_file, mock_stat, mock_isfile):
    """Test hard duplicate upload (409 Conflict)."""
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1600000000
    mock_stat.return_value.st_ctime = 1600000000

    mock_post.return_value.status_code = 409
    mock_post.return_value.json.return_value = {"id": "existing_asset_id"}

    asset_id = uploader_v1.upload_asset(
        "/fake/path/image.jpg", "http://mock_url", "api_key"
    )
    assert asset_id == "existing_asset_id"


@patch("os.path.isfile", return_value=True)
@patch("os.stat")
@patch("builtins.open", new_callable=mock_open, read_data=b"mock data")
@patch("requests.post")
def test_upload_asset_hard_duplicate_no_json(
    mock_post, mock_file, mock_stat, mock_isfile
):
    """Test hard duplicate upload (409 Conflict) without JSON response containing ID."""
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1600000000
    mock_stat.return_value.st_ctime = 1600000000

    mock_post.return_value.status_code = 409
    mock_post.return_value.json.side_effect = ValueError("No JSON")

    asset_id = uploader_v1.upload_asset(
        "/fake/path/image.jpg", "http://mock_url", "api_key"
    )
    assert asset_id == "DUPLICATE_UNKNOWN_ID"


@patch("os.path.isfile", return_value=True)
@patch("os.stat")
@patch("builtins.open", new_callable=mock_open, read_data=b"mock data")
@patch("requests.post")
def test_upload_asset_error(mock_post, mock_file, mock_stat, mock_isfile):
    """Test file upload failure (500 Server Error)."""
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1600000000
    mock_stat.return_value.st_ctime = 1600000000

    mock_post.return_value.status_code = 500
    # The actual implementation calls response.raise_for_status() on 500
    mock_post.return_value.raise_for_status.side_effect = (
        requests.exceptions.HTTPError()
    )

    asset_id = uploader_v1.upload_asset(
        "/fake/path/image.jpg", "http://mock_url", "api_key"
    )
    assert asset_id is None


def test_load_history():
    """Test loading upload history."""
    mock_data = '["image1.jpg", "image2.jpg"]'
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            history = uploader_v1.load_history()
            assert history == {"image1.jpg", "image2.jpg"}


def test_load_history_empty():
    """Test loading empty or non-existent upload history."""
    with patch("os.path.exists", return_value=False):
        history = uploader_v1.load_history()
        assert history == set()

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=ValueError):  # simulate parse error
            history = uploader_v1.load_history()
            assert history == set()


def test_save_history():
    """Test saving upload history."""
    history = {"image1.jpg", "image2.jpg"}
    mock_file = mock_open()

    with patch("builtins.open", mock_file):
        uploader_v1.save_history(history)

    mock_file.assert_called_once_with(uploader_v1.HISTORY_FILE, "w")
    # Verify write was called (json.dump writes in chunks usually, so just asserting call count/args)
    assert mock_file().write.called


@patch("uploader_v1.get_active_url")
@patch("uploader_v1.get_album_id")
@patch("uploader_v1.load_history")
@patch("uploader_v1.upload_asset")
@patch("uploader_v1.add_to_album")
@patch("uploader_v1.save_history")
@patch("os.listdir")
@patch("os.path.isfile")
@patch("os.path.getmtime")
def test_main_success(
    mock_getmtime,
    mock_isfile,
    mock_listdir,
    mock_save_history,
    mock_add_to_album,
    mock_upload_asset,
    mock_load_history,
    mock_get_album_id,
    mock_get_active_url,
    mock_env,
):
    """Test the main processing loop."""
    # Setup mock returns
    mock_get_active_url.return_value = "http://localhost:2283"
    mock_get_album_id.return_value = "album_123"
    mock_load_history.return_value = {"old_image.jpg"}
    mock_listdir.return_value = ["old_image.jpg", "new_image.jpg", "not_an_image.txt"]
    mock_isfile.return_value = True
    mock_getmtime.return_value = 12345
    mock_upload_asset.return_value = "new_asset_123"

    # with patch dict to mock constant
    with patch("os.path.exists", return_value=True):
        uploader_v1.main()

    # Validate the correct image was processed and others skipped
    mock_upload_asset.assert_called_once()
    assert mock_upload_asset.call_args[0][0].endswith("new_image.jpg")
    mock_add_to_album.assert_called_once_with(
        "http://localhost:2283", "mock_api_key", "album_123", "new_asset_123"
    )
    mock_save_history.assert_called_once()
    assert "new_image.jpg" in mock_save_history.call_args[0][0]


@patch("uploader_v1.get_active_url")
def test_main_no_url(mock_get_active_url, mock_env):
    """Test main when no URL is available."""
    mock_get_active_url.return_value = None
    with patch("os.path.exists", return_value=True):
        uploader_v1.main()
    # It should exit early, no other methods called


@patch("uploader_v1.get_active_url")
@patch("uploader_v1.get_album_id")
def test_main_no_album(mock_get_album_id, mock_get_active_url, mock_env):
    """Test main when album is not found."""
    mock_get_active_url.return_value = "http://localhost:2283"
    mock_get_album_id.return_value = None
    with patch("os.path.exists", return_value=True):
        uploader_v1.main()
    # It should exit early, no other methods called
