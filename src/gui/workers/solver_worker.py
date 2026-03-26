"""QThread worker for running the solver off the main thread."""

from PySide6.QtCore import QThread, Signal


class SolverWorker(QThread):
    """Run solve_multi_period_NBA in a background thread."""

    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, all_data, squad, sell_prices, gd, itb, options, parent=None):
        super().__init__(parent)
        self.all_data = all_data
        self.squad = squad
        self.sell_prices = sell_prices
        self.gd = gd
        self.itb = itb
        self.options = options

    def run(self):
        try:
            from solve import solve_multi_period_NBA

            self.progress.emit("Solver started...")
            result = solve_multi_period_NBA(
                all_data=self.all_data,
                squad=self.squad,
                sell_prices=self.sell_prices,
                gd=self.gd,
                itb=self.itb,
                options=self.options,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
