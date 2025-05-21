import pytest
from unittest import mock

import scripts.seed_database as seed_database_script

def make_env(llm_provider="openai", extra_vars=None):
    env = {
        "MONGODB_ATLAS_URI": "mongodb://fake",
        "TENANT_ID": "tenant",
        "CLIENT_ID": "client",
        "CLIENT_SECRET": "secret",
        "SITE_ID": "site",
        "OPENAI_API_KEY": "openai-key",
        "ADMIN_EMAIL": "admin@example.com"
    }
    if llm_provider == "anthropic":
        env["ANTHROPIC_API_KEY"] = "anthropic-key"
        env.pop("OPENAI_API_KEY", None)
    elif llm_provider == "azure":
        env["AZURE_API_KEY"] = "azure-key"
        env.pop("OPENAI_API_KEY", None)
    if extra_vars:
        env.update(extra_vars)
    return env

@mock.patch("scripts.seed_database.print")
@mock.patch("scripts.seed_database.seed_database")
@mock.patch("scripts.seed_database.MongoClient")
@mock.patch("scripts.seed_database.settings")
@mock.patch("scripts.seed_database.os")
@mock.patch("scripts.seed_database.sys")
def test_main_success(
    mock_sys, mock_os, mock_settings, mock_MongoClient, mock_seed_database, mock_print
):
    mock_sys.argv = ["seed_database.py"]
    mock_os.getenv.side_effect = lambda k: make_env()[k]
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.DB_NAME = "testdb"
    mock_settings.MONGODB_ATLAS_URI = "mongodb://fake"
    mock_seed_database.return_value = 42
    mock_MongoClient.return_value = mock.Mock()
    mock_sys.exit = mock.Mock()
    # Patch argparse to simulate no --admin-email
    with mock.patch("scripts.seed_database.argparse.ArgumentParser.parse_args", return_value=mock.Mock(admin_email=None)):
        seed_database_script.main()
    assert mock_seed_database.called
    assert any("Successfully seeded database" in str(c[0][0]) for c in mock_print.call_args_list)
    assert not mock_sys.exit.called
    mock_MongoClient.return_value.close.assert_called_once()

@mock.patch("scripts.seed_database.print")
@mock.patch("scripts.seed_database.settings")
@mock.patch("scripts.seed_database.os")
@mock.patch("scripts.seed_database.sys")
@mock.patch("scripts.seed_database.MongoClient")
def test_main_missing_env_vars(
    mock_MongoClient, mock_sys, mock_os, mock_settings, mock_print
):
    # Simulate missing TENANT_ID
    env = make_env()
    env.pop("TENANT_ID")
    mock_sys.argv = ["seed_database.py"]
    mock_os.getenv.side_effect = lambda k: env.get(k)
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.DB_NAME = "testdb"
    mock_sys.exit.side_effect = SystemExit  # <-- Make sys.exit() raise SystemExit
    with mock.patch("scripts.seed_database.argparse.ArgumentParser.parse_args", return_value=mock.Mock(admin_email=None)):
        try:
            seed_database_script.main()
        except SystemExit:
            pass
    assert any("Missing required environment variables" in str(c[0][0]) for c in mock_print.call_args_list)
    mock_sys.exit.assert_called_once_with(1)

@mock.patch("scripts.seed_database.print")
@mock.patch("scripts.seed_database.seed_database")
@mock.patch("scripts.seed_database.MongoClient")
@mock.patch("scripts.seed_database.settings")
@mock.patch("scripts.seed_database.os")
@mock.patch("scripts.seed_database.sys")
def test_main_seed_database_exception(
    mock_sys, mock_os, mock_settings, mock_MongoClient, mock_seed_database, mock_print
):
    mock_sys.argv = ["seed_database.py"]
    mock_os.getenv.side_effect = lambda k: make_env()[k]
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.DB_NAME = "testdb"
    mock_settings.MONGODB_ATLAS_URI = "mongodb://fake"
    mock_seed_database.side_effect = Exception("fail!")
    mock_MongoClient.return_value = mock.Mock()
    mock_sys.exit = mock.Mock()
    with mock.patch("scripts.seed_database.argparse.ArgumentParser.parse_args", return_value=mock.Mock(admin_email=None)):
        seed_database_script.main()
    assert any("Failed to seed database" in str(c[0][0]) for c in mock_print.call_args_list)
    mock_sys.exit.assert_called_once_with(1)
    mock_MongoClient.return_value.close.assert_called_once()

@mock.patch("scripts.seed_database.print")
@mock.patch("scripts.seed_database.seed_database")
@mock.patch("scripts.seed_database.MongoClient")
@mock.patch("scripts.seed_database.settings")
@mock.patch("scripts.seed_database.os")
@mock.patch("scripts.seed_database.sys")
def test_main_admin_email_arg_overrides_env(
    mock_sys, mock_os, mock_settings, mock_MongoClient, mock_seed_database, mock_print
):
    env = make_env()
    env["ADMIN_EMAIL"] = "env_admin@example.com"
    mock_sys.argv = ["seed_database.py", "--admin-email", "cli_admin@example.com"]
    mock_os.getenv.side_effect = lambda k: env.get(k)
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.DB_NAME = "testdb"
    mock_settings.MONGODB_ATLAS_URI = "mongodb://fake"
    mock_seed_database.return_value = 5
    mock_MongoClient.return_value = mock.Mock()
    mock_sys.exit = mock.Mock()
    with mock.patch("scripts.seed_database.argparse.ArgumentParser.parse_args", return_value=mock.Mock(admin_email="cli_admin@example.com")):
        seed_database_script.main()
    mock_seed_database.assert_called_with(mock.ANY, "cli_admin@example.com")
    mock_MongoClient.return_value.close.assert_called_once()

@mock.patch("scripts.seed_database.print")
@mock.patch("scripts.seed_database.seed_database")
@mock.patch("scripts.seed_database.MongoClient")
@mock.patch("scripts.seed_database.settings")
@mock.patch("scripts.seed_database.os")
@mock.patch("scripts.seed_database.sys")
def test_main_admin_email_env_used(
    mock_sys, mock_os, mock_settings, mock_MongoClient, mock_seed_database, mock_print
):
    env = make_env()
    env["ADMIN_EMAIL"] = "env_admin@example.com"
    mock_sys.argv = ["seed_database.py"]
    mock_os.getenv.side_effect = lambda k: env.get(k)
    mock_settings.LLM_PROVIDER = "openai"
    mock_settings.DB_NAME = "testdb"
    mock_settings.MONGODB_ATLAS_URI = "mongodb://fake"
    mock_seed_database.return_value = 5
    mock_MongoClient.return_value = mock.Mock()
    mock_sys.exit = mock.Mock()
    with mock.patch("scripts.seed_database.argparse.ArgumentParser.parse_args", return_value=mock.Mock(admin_email=None)):
        seed_database_script.main()
    mock_seed_database.assert_called_with(mock.ANY, "env_admin@example.com")
    mock_MongoClient.return_value.close.assert_called_once()