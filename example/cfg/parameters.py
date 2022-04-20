import numpy as np
from matplotlib.colors import ListedColormap, LinearSegmentedColormap


# ------------------------------------------ CONFIG
# Medium parameters
speed_of_sound = 2900
# TX/RX parameters
tx_frequency = 18e6
rx_sample_range_us = (0e-6, 61.5e-6)  # [s]

# Pulse Repetition Interval
pri = 200e-6  # [s]
# Poczatkowy gain (zaraz po wlaczeniu aplikacji)
initial_gain = 54  # [dB]
# Poczatkowe napiecie (zaraz po wlaczeniu aplikacji)
initial_voltage = 15
# Dzielnik czestotliwosci probkowania
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
x_grid = np.arange(-40, 50, 0.2) * 1e-3 # [m]
# Polozenie punktow siatki docelowej S-scan, wspolrzedna OX
z_grid = np.arange(0, 60, 0.2) * 1e-3

# Zakres dynamiki
dynamic_range = (0, 100)  # [dB] or a.u. w zaleznosci od tego, czy wlaczona jest kompresja logarytmiczna

# Kolormapa
# OPCJA 1. Skala szarosci
colormap = "gray" # Skala szarosci
# OPCJA 2. kolormapa taka jak w OmniPC
cdict = {'red':   [[0.0, 1.0, 1.0],
                   [0.4, 0.0, 0.0],
                   [0.5, 0.0, 0.0],
                   [0.6, 1.0, 1.0],
                   [1.0, 1.0, 1.0]
                  ],
         'green': [[0.0, 1.0, 1.0],
                   [0.4, 0.0, 0.0],
                   [0.5, 1.0, 1.0],
                   [0.6, 1.0, 1.0],
                   [1.0, 0.0, 0.0]
                  ],
         'blue':  [[0.0, 1.0, 1.0],
                   [0.4, 1.0, 1.0],
                   [0.5, 0.0, 0.0],
                   [0.6, 0.0, 0.0],
                   [1.0, 0.0, 0.0]
                  ]}
omnipc_cmap = LinearSegmentedColormap('omnipc', segmentdata=cdict, N=256)
omnipc_cmap.set_bad(color="black")
# ODKOMENTUJ PONIZSZA LINIE, ZEBY WLACZYC KOLORMAPE OmniPC
# colormap = omnipc_cmap


capture_buffer_capacity = 500
