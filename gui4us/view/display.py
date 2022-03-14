from gui4us.view.widgets import Panel


class DisplayPanel(Panel):

    def __init__(self, title="Display"):
        super().__init__(title)
        settings = self._controller.settings
        display_panel_widget = QGroupBox("RF data")
        display_panel_layout = QHBoxLayout()
        display_panel_widget.setLayout(display_panel_layout)
        img_canvas = FigureCanvas(Figure(figsize=(6, 6)))
        self.addToolBar(QtCore.Qt.BottomToolBarArea,
                        NavigationToolbar(img_canvas, self))

        display_panel_layout.addWidget(img_canvas)
        ax = img_canvas.figure.subplots()
        ax.set_xlabel("Azimuth [mm]")
        ax.set_ylabel("Acquisition time [us]")
        ax.set_title("Press start button...")
        self.extent_ox = np.array(settings["image_extent_ox"]) * 1e3
        self.extent_oz = np.array(settings["image_extent_oz"])
        self._current_gain_value = settings["tgc_start"]

        empty_input = np.zeros((settings["n_pix_oz"], settings["n_pix_ox"]), dtype=np.float32)
        self.img_canvas = ax.imshow(empty_input, cmap="gray",
                                    vmin=-100, vmax=100,
                                    extent=[self.extent_ox[0], self.extent_ox[1],
                                            self.extent_oz[1], self.extent_oz[0]])
        alphas = np.zeros((settings["n_pix_oz"], settings["n_pix_ox"]), dtype=np.float32)
        self.img_canvas2 = ax.imshow(empty_input, cmap="YlOrRd", vmin=0, vmax=2,
                                     extent=[self.extent_ox[0], self.extent_ox[1],
                                             self.extent_oz[1], self.extent_oz[0]])
        # self.img_canvas.figure.colorbar(self.img_canvas)
        self.img_canvas.figure.tight_layout()

        # View worker
        self.thread = QThread()
        self.worker = ViewWorker(self._update_canvas)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self._last_rf_trigger = None

    def _update_canvas(self):
        try:
            if self._current_state == _STARTED:
                data_mask = self._controller.get_defect_mask().T
                rf_sum = self._controller.get_rf_sum().T
                rf = self._controller.get_rf()

                if self._current_state == _STOPPED or rf is None or rf_sum is None:
                    # Just discard results if the current device now is stopped
                    # (e.g. when the save button was pressed).
                    return

                if self._rf_buffer_state == _CAPTURING:
                    current_trigger = rf[0, 0]

                    data_correctness_msg = "correct"
                    if self._last_rf_trigger is not None:
                        trigger_diff = current_trigger - self._last_rf_trigger
                        if trigger_diff != 32:
                            data_correctness_msg = f"INCORRECT (trigger difference: {trigger_diff})"

                    self._last_rf_trigger = current_trigger

                    self.statusBar().showMessage(f"Captured frame {len(self._rf_buffer.data)}, "
                                                 f"current trigger: {current_trigger}, "
                                                 f"data: {data_correctness_msg}")

                    # bmode, mask, RF, gain, voltage
                    self._rf_buffer.append((rf_sum, data_mask, rf, self._current_gain_value,
                                            self._voltage_spin_box.value()))
                    if self._rf_buffer.is_ready():
                        self._last_rf_trigger = None
                        self._update_buffer_state_graph(_CAPTURE_DONE)
                self.img_canvas.axes.set_title(f"FMC, gain: {self._current_gain_value} [dB]")
                self.img_canvas.set_data(rf_sum)
                self.img_canvas2.set_data(data_mask)
                alpha = (data_mask != 0.0).astype(np.float32)
                self.img_canvas2.set_alpha(alpha)
                self.img_canvas.figure.canvas.draw()
        except Exception as e:
            print(e)

