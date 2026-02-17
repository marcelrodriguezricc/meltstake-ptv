import numpy as np
import matplotlib.pyplot as plt

# ----- VARIABLES -----

# Camera constraints
focal_length = 3
res_x = 1600
res_y = 1200
pixel_pitch = 0.003 

# Disparity uncertainty
sigma_d = 0.5

# Depth range (mm)
Zmin = 100
Zmax = 602

# Fixed baseline (mm)
b_fixed = 148

# ----- FUNCTIONS -----

def depth_sigma_Z(b_mm, Z_mm, f_px, sigma_d_px):
    """Depth uncertainty σZ (mm) from disparity uncertainty σd (px)."""
    b_mm = np.maximum(b_mm, 1e-9)
    return (Z_mm**2 / (f_px * b_mm)) * sigma_d_px

# ----- CALCULATIONS -----

# Focal length in pixels
fl_pixels = focal_length / pixel_pitch

# Depth samples
Zs = np.linspace(Zmin, Zmax, 800)

# Depth uncertainty vs depth for fixed baseline
sigZ = depth_sigma_Z(b_fixed, Zs, fl_pixels, sigma_d)

# ----- PLOT -----

plt.figure()
plt.plot(Zs, sigZ, label=rf"$b={b_fixed}$ mm, $\sigma_d={sigma_d}$ px")
plt.xlabel("Depth Z (mm)")
plt.ylabel(r"Depth uncertainty $\sigma_Z$ (mm)")
plt.grid(True)
plt.title("Depth uncertainty vs depth (fixed baseline)")
plt.legend()
plt.show()
