import numpy as np

# ------------------------------------------ CONFIG

# Medium parameters
speed_of_sound = 2900
# TX/RX parameters
tx_frequency = 5e6
rx_sample_range_us = (0e-6, 61.5e-6)  # [s]

pri = 200e-6
initial_gain = 54
initial_voltage = 50
downsampling_factor = 1
sampling_frequency = 65e6 / downsampling_factor

# Klin
# predkosc dzwieku
wedge_speed_of_sound = 2320  # [m/s]
# Odleglosc dolnej krawedzi klinu od srodka glowicy (pod katem prostym).
wedge_size = 21e-3  # [m]
# Kat nachylenia glowicy do klinu.
wedge_angle = 35.8*np.pi/180 # [rad]

# Polozenie punktow siatki docelowej S-scan, wspolrzedna OX
x_grid = np.arange(-20, 50, 0.2) * 1e-3 # [m]
# Polozenie punktow siatki docelowej S-scan, wspolrzedna OX
z_grid = np.arange(0, 60, 0.2) * 1e-3

# Zakres dynamiki
dynamic_range = (20, 80)  # [dB]
# Kolormapa
colormap = "gray"

capture_buffer_capacity = 500