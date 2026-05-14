from rv.config import Config, load_config


class TestLoadConfig:
    @staticmethod
    def test_loads_default_config_when_no_file(tmp_path):
        config_file = tmp_path / "config.toml"
        config = load_config(config_file)
        assert config.stale_threshold_minutes == 5
        assert config.canned_replies == {}

    @staticmethod
    def test_loads_config_from_file(tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[sync]
stale_threshold_minutes = 10

[canned_replies]
fixed = "Fixed."
wip = "Working on it"
""")
        config = load_config(config_file)
        assert config.stale_threshold_minutes == 10
        assert config.canned_replies == {"fixed": "Fixed.", "wip": "Working on it"}

    @staticmethod
    def test_missing_sync_section_uses_default(tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[canned_replies]
fixed = "Fixed."
""")
        config = load_config(config_file)
        assert config.stale_threshold_minutes == 5

    @staticmethod
    def test_missing_canned_replies_section_empty(tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[sync]
stale_threshold_minutes = 15
""")
        config = load_config(config_file)
        assert config.canned_replies == {}


class TestConfig:
    @staticmethod
    def test_config_has_expected_defaults():
        config = Config()
        assert config.stale_threshold_minutes == 5
        assert config.canned_replies == {}

    @staticmethod
    def test_config_with_custom_values():
        config = Config(stale_threshold_minutes=10, canned_replies={"fixed": "Fixed."})
        assert config.stale_threshold_minutes == 10
        assert config.canned_replies == {"fixed": "Fixed."}
