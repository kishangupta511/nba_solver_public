"""QThread workers for data refresh, team retrieval, and xMins apply."""

from PySide6.QtCore import QThread, Signal


class DataRefreshWorker(QThread):
    """Run refresh_data() in a background thread."""

    finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            from run import refresh_data
            refresh_data()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class RetrieveSquadWorker(QThread):
    """Run get_team() in a background thread."""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, team_id: int, parent=None):
        super().__init__(parent)
        self.team_id = team_id

    def run(self):
        try:
            from retrieve import get_team
            result = get_team(self.team_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class XminsApplyWorker(QThread):
    """Apply a batched xMins edit set off the UI thread."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, service, edits: list[dict], parent=None):
        super().__init__(parent)
        self._service = service
        self._edits = edits

    def run(self):
        try:
            result = self._service.apply_edits(self._edits)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
