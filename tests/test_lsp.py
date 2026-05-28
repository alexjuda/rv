from unittest.mock import MagicMock, patch

from lsprotocol import types
from rv.lsp import RVServer


class TestLSPDiagnostics:
    @staticmethod
    def test_diagnostic_severity_is_hint():
        diag = types.Diagnostic(
            range=MagicMock(), message="test", severity=types.DiagnosticSeverity(4)
        )
        assert diag.severity == types.DiagnosticSeverity(4)


class TestRVServer:
    @staticmethod
    def test_rv_server_imports():
        assert RVServer is not None


class TestWatchfilesIntegration:
    @staticmethod
    @patch("rv.lsp.watchfiles")
    def test_server_uses_watchfiles(mock_watchfiles):
        mock_watchfiles.watch.return_value = iter([])

        server = RVServer()
        assert hasattr(server, "_watcher")
        mock_watchfiles.watch.assert_called_once()

    @staticmethod
    def test_on_file_change_reloads_threads():
        with patch("rv.lsp.watchfiles") as mock_wf:
            mock_wf.watch.return_value = iter([])
            server = RVServer()
            server._owner = "owner"
            server._repo = "repo"
            server._pr_number = 1

            with patch.object(server, "_reload_threads") as mock_reload:
                server._on_file_change({"change"})
                mock_reload.assert_called_once()
