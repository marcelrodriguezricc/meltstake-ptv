import numpy as np
import matplotlib.pyplot as plt

# ----- VARIABLES -----

# Camera specifications
focal_length = 3 # mm
res_x = 1600 # pixels
res_y = 1200 # pixels
pixel_pitch = 0.003 # mm
f_stop = 1.6 # ratio (focal length / effective aperture diameter)

# Baseline and focus length constraints (mm)
b_min = 50
b_max = 400
focus_min = 100
focus_max = 250

# Required depth disparity (mm)
sigmaZ_req = 0.5

# Estimated baseline disparity at 100m
sigma_b = 1.0

# ----- FUNCTIONS -----

def depth_of_field_mm(subject_distance_mm, focal_length_mm, f_number, coc_mm):
    s = float(subject_distance_mm)
    f = float(focal_length_mm)
    N = float(f_number)
    c = float(coc_mm)

    H = (f * f) / (N * c) + f

    near = (H * s) / (H + (s - f))

    if s >= H:
        far = np.inf
    else:
        far = (H * s) / (H - (s - f))

    dof = far - near if np.isfinite(far) else np.inf
    return near, far, dof, H

def fov(Z_mm, theta):
    return 2 * Z_mm * np.tan(theta / 2)

def depth_sigma_Z(b_mm, Z_mm, f_px, sigma_d_px):
    return (Z_mm**2 / (f_px * b_mm)) * sigma_d_px

def overlap_area_at_Z(b_mm, Z_mm, theta_x, theta_y):
    W = fov(Z_mm, theta_x)
    H = fov(Z_mm, theta_y)
    W_ov = np.maximum(0, W - b_mm)
    return W_ov * H

def resolvable_volume_for_baseline(b_mm, Zmin, Zmax):
    if not np.isfinite(Zmin) or not np.isfinite(Zmax) or (Zmax <= Zmin):
        return 0.0

    Zs = np.linspace(Zmin, Zmax, 2000)
    Aov = overlap_area_at_Z(b_mm, Zs, theta_x, theta_y)
    sigZ = depth_sigma_Z(b_mm, Zs, fl_pixels, sigma_d)
    limit_workspace = np.where(sigZ <= sigmaZ_req, Aov, 0.0)
    V = np.trapezoid(limit_workspace, Zs)
    return V

def sigma_d_of_Z(Z, sigma0=0.5, beta=0.01, Z0=100.0):
    Z = np.asarray(Z, dtype=float)
    return sigma0 * np.maximum(0.0, np.exp(beta*(Z - Z0)) - 1.0)

# ----- CALCULATIONS -----

# Convert focal length to pixels
fl_pixels = focal_length / pixel_pitch

# Calculate physical sensor dimensions
sensor_w = res_x * pixel_pitch
sensor_h = res_y * pixel_pitch

# Get field of view angles
theta_x = 2 * np.arctan(sensor_w / (2 * focal_length))
theta_y = 2 * np.arctan(sensor_h / (2 * focal_length))

# Sweep through a range of focus distances
focus_sweep_mm = np.linspace(100, 250, 10)

# Sweep through a range of baselines
b_sweep = np.linspace(b_min, b_max, 400)

# Store best volume for each focus distance
V_best = np.zeros_like(focus_sweep_mm)
b_opt_list = np.zeros_like(focus_sweep_mm)

for i, focus_distance in enumerate(focus_sweep_mm):

    # Compute DOF bounds
    near, far, dof, H = depth_of_field_mm(
        subject_distance_mm=focus_distance,
        focal_length_mm=focal_length,
        f_number=f_stop,
        coc_mm=pixel_pitch
    )

    # Update sigma_d for this focus distance
    sigma_d = float(sigma_d_of_Z(focus_distance, sigma_b))

    # Optimize baseline
    V = np.array([resolvable_volume_for_baseline(bi, near, far) for bi in b_sweep])
    j = np.argmax(V)
    V_best[i] = V[j]
    b_opt_list[i] = b_sweep[j]

# Plot
plt.figure()
plt.plot(focus_sweep_mm, V_best) 
plt.scatter(focus_sweep_mm, V_best) 

# Add labels at each point
for x, y, bopt in zip(focus_sweep_mm, V_best, b_opt_list):
    plt.annotate(f"{x:.0f}mm\n$b_o$={bopt:.0f}mm", (x, y),
             textcoords="offset points", xytext=(12, -8),
             ha="left", fontsize=7)
    

plt.xlabel("Focus distance (mm)")
plt.ylabel("Max resolvable volume (mm$^3$)")
plt.title(f"Focus Distance vs Max Resolvable Volume - Baseline Disparity {sigma_b}")
plt.grid(True)
plt.show()