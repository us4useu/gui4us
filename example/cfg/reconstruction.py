import cupy as cp
from arrus.utils.imaging import *


def _get_const_memory_array(module, name, input_array):
    import cupy as cp
    const_arr_ptr = module.get_global(name)
    const_arr = cp.ndarray(input_array.shape, dtype=input_array.dtype,
                           memptr=const_arr_ptr)
    const_arr.set(input_array)
    return const_arr


# Reconstruction code
class ReconstructLriWedge(Operation):
    """
    NOTE: This implementation works correctly only with SSTA.

    Rx beamforming for synthetic aperture imaging.

    Expected input data shape: n_emissions, n_rx, n_samples
    :param x_grid: output image grid points (OX coordinates)
    :param z_grid: output image grid points  (OZ coordinates)
    :param rx_tang_limits: RX apodization angle limits (given as the tangent of the angle), \
      a pair of values (min, max). If not provided or None, [-0.5, 0.5] range will be used
    """

    def __init__(self, x_grid, z_grid,
                 wedge_speed_of_sound,
                 wedge_size,
                 wedge_angle,
                 rx_tang_limits=None):
        self.x_grid = x_grid
        self.z_grid = z_grid
        self.wedge_speed_of_sound = wedge_speed_of_sound
        self.wedge_size = wedge_size
        self.wedge_angle = wedge_angle
        import cupy as cp
        self.num_pkg = cp
        self.rx_tang_limits = rx_tang_limits # Currently used only by Convex PWI implementation

    def set_pkgs(self, num_pkg, **kwargs):
        if num_pkg is np:
            raise ValueError("ReconstructLri operation is implemented for GPU only.")

    def prepare(self, const_metadata):
        import cupy as cp

        current_dir = os.path.dirname(os.path.join(os.path.abspath(__file__)))
        _kernel_source = Path(os.path.join(current_dir, "iq_raw_2_lri_wedge.cu")).read_text()
        self._kernel_module = self.num_pkg.RawModule(code=_kernel_source)
        self._kernel = self._kernel_module.get_function("iqRaw2Lri")
        self._z_elem_const = self._kernel_module.get_global("zElemConst")
        self._tang_elem_const = self._kernel_module.get_global("tangElemConst")

        # INPUT PARAMETERS.
        # Input data shape.
        self.n_seq, self.n_tx, self.n_rx, self.n_samples = const_metadata.input_shape

        seq = const_metadata.context.sequence
        probe_model = const_metadata.context.device.probe.model
        acq_fs = (const_metadata.context.device.sampling_frequency / seq.downsampling_factor)
        start_sample = seq.rx_sample_range[0]

        self.x_size = len(self.x_grid)
        self.z_size = len(self.z_grid)
        output_shape = (self.n_seq, self.n_tx, self.x_size, self.z_size)
        self.output_buffer = self.num_pkg.zeros(output_shape, dtype=self.num_pkg.complex64)
        x_block_size = min(self.x_size, 16)
        z_block_size = min(self.z_size, 16)
        tx_block_size = min(self.n_tx, 4)
        self.block_size = (z_block_size, x_block_size, tx_block_size)
        self.grid_size = (int((self.z_size-1)//z_block_size + 1),
                          int((self.x_size-1)//x_block_size + 1),
                          int((self.n_seq*self.n_tx-1)//tx_block_size + 1))
        self.x_pix = self.num_pkg.asarray(self.x_grid, dtype=self.num_pkg.float32)
        self.z_pix = self.num_pkg.asarray(self.z_grid, dtype=self.num_pkg.float32)

        # System and transmit properties.
        self.sos = self.num_pkg.float32(seq.speed_of_sound)
        self.fs = self.num_pkg.float32(const_metadata.data_description.sampling_frequency)
        self.fn = self.num_pkg.float32(seq.pulse.center_frequency)
        self.pitch = self.num_pkg.float32(probe_model.pitch)
        self.wedge_sos = self.num_pkg.float32(self.wedge_speed_of_sound)

        # Probe description
        # coordinate system centered on the probe
        element_pos_x_orig = probe_model.element_pos_x
        element_pos_z_orig = probe_model.element_pos_z
        # coordinate system centered over the wedge, probe rotated according to
        # the wedge geometry.
        element_pos_x = element_pos_x_orig * np.cos(self.wedge_angle) \
                      + element_pos_z_orig * np.sin(self.wedge_angle)
        element_pos_z = element_pos_z_orig * np.cos(self.wedge_angle) \
                      - element_pos_x_orig * np.sin(self.wedge_angle) \
                      - self.wedge_size
        element_angle = probe_model.element_angle + self.wedge_angle
        element_angle_tang = np.tan(element_angle)

        self.n_elements = probe_model.n_elements

        device_props = cp.cuda.runtime.getDeviceProperties(0)
        if device_props["totalConstMem"] < 256*3*4:  # 3 float32 arrays, 256 elements max
            raise ValueError("There is not enough constant memory available!")

        x_elem = np.asarray(element_pos_x, dtype=self.num_pkg.float32)
        self._x_elem_const = _get_const_memory_array(
            self._kernel_module, name="xElemConst", input_array=x_elem)
        z_elem = np.asarray(element_pos_z, dtype=self.num_pkg.float32)
        self._z_elem_const = _get_const_memory_array(
            self._kernel_module, name="zElemConst", input_array=z_elem)
        tang_elem = np.asarray(element_angle_tang, dtype=self.num_pkg.float32)
        self._tang_elem_const = _get_const_memory_array(
            self._kernel_module, name="tangElemConst", input_array=tang_elem)

        # NOTE: this will work only with sequences which as the
        # tx_aperture_center_element set.
        tx_center_z = np.interp(seq.tx_aperture_center_element,
                                np.arange(0, self.n_elements),
                                np.squeeze(element_pos_z))
        tx_center_x = np.interp(seq.tx_aperture_center_element,
                                np.arange(0, self.n_elements),
                                np.squeeze(element_pos_x))
        self.tx_ap_cent_x = self.num_pkg.asarray(tx_center_x, dtype=self.num_pkg.float32)
        self.tx_ap_cent_z = self.num_pkg.asarray(tx_center_z, dtype=self.num_pkg.float32)

        # first/last probe element in TX aperture
        # NOTE: this will work only with full RX aperture
        rx_ap_origin = 0 # np.round(rx_centers-(rx_sizes-1)/2 + 1e-9).astype(np.int32)
        self.rx_ap_origin = self.num_pkg.asarray(rx_ap_origin, dtype=self.num_pkg.int32)

        # Min/max tang
        if self.rx_tang_limits is not None:
            self.min_tang, self.max_tang = self.rx_tang_limits
        else:
            # Default:
            self.min_tang, self.max_tang = -0.5, 0.5

        # NOTE: this will work only with SSTA
        tx_center_delay = 0.0
        self.min_tang = self.num_pkg.float32(self.min_tang)
        self.max_tang = self.num_pkg.float32(self.max_tang)
        burst_factor = seq.pulse.n_periods / (2*self.fn)
        self.initial_delay = -start_sample/65e6+burst_factor+tx_center_delay
        self.initial_delay = self.num_pkg.float32(self.initial_delay)

        self.time_precision = 1/64/self.fn
        self.time_precision = self.num_pkg.float32(self.time_precision)

        return const_metadata.copy(input_shape=output_shape)

    def process(self, data):
        data = self.num_pkg.ascontiguousarray(data)
        params = (
            self.output_buffer,
            data,
            self.n_elements,
            self.n_seq, self.n_tx, self.n_samples,
            self.z_pix, self.z_size,
            self.x_pix, self.x_size,
            self.sos, self.fs, self.fn,
            self.tx_ap_cent_z, self.tx_ap_cent_x,
            self.rx_ap_origin, self.n_rx,
            self.min_tang, self.max_tang,
            self.initial_delay,
            self.wedge_sos,
            self.time_precision
        )
        self._kernel(self.grid_size, self.block_size, params)
        return self.output_buffer


class PhaseCoherenceWeighting(Operation):

    def __init__(self):
        pass

    def set_pkgs(self, num_pkg, **kwargs):
        self.num_pkg = num_pkg

    def prepare(self, const_metadata):
        return const_metadata

    def process(self, data):
        amp = self.num_pkg.abs(data)
        r = self.num_pkg.real(data)
        im = self.num_pkg.imag(data)
        ccf = 1 - self.num_pkg.sqrt(self.num_pkg.nanvar(r/amp, axis=1)
                                    + self.num_pkg.nanvar(im/amp, axis=1))
        return data*ccf