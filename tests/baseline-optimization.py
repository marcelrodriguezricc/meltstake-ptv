import numpy as np
import matplotlib.pyplot as plt

# ----- VARIABLES -----

# Camera constraints
focal_length = 3 # Focal length in mm, specified by stellarHD documentation
res_x = 1600 # Sensor array pixels-per-row, specified by OG02B1B documentation
res_y = 1200 # Sensor array pixels-per-column, specified by OG02B1B documentation
pixel_pitch = 0.003 # Distance between center of each pixel in mm

# Disparity uncertainty
sigma_d = 1.0 # Conservative estimate for underwater scene, std. dev. noise in pixels

# Target requirements
sigmaZ_req = 1.0 # Maximum allowed std. dev. depth uncertainty
Zmin = 100 # Minimum resolvable depth in mm, set based on camera lens minimum focus distance
Zmax = 602 # Maximum resolvable depth in mm, set based on distance from sensor to surface of ice

# Possible baseline range
b_min = 50 # Minimum baseline range, based on width of camera (approximate pinhole distance if they were touching)
b_max = 500 # Maximum baseline range, chosen arbitrarily

# Modeling parameters
num_samples = 10000

# ----- FUNCTIONS -----

def fov(Z_mm, theta):
    """"Get field of view given depth and angle"""
    return 2 * Z_mm * np.tan(theta / 2) # Get linear FOV by solving for right triangle, where half of the scene is the opposite side, and the depth is the adjacent side

def depth_sigma_Z(b_mm, Z_mm, f_px, sigma_d_px):
    """Calculate depth disparity, given baseline, depth, focal length, and disparity"""
    return (Z_mm**2 / (f_px * b_mm)) * sigma_d_px # Disparity formula with depth uncertainty multiplier in pixels

def overlap_area_at_Z(b_mm, Z_mm, theta_x, theta_y):
    """Calculate overlap between two cameras given baseline, depth, and fov angles"""
    W = fov(Z_mm, theta_x) # Scene width
    H = fov(Z_mm, theta_y) # Scene height
    W_ov = np.maximum(0, W - b_mm) # Subtract width from baseline to get overlap
    return W_ov * H # Multiply by height to return area

def resolvable_volume_for_baseline(b_mm):
    Zs = np.linspace(Zmin, Zmax, num_samples) # Discretize depth axis (approximate integral)
    Aov = overlap_area_at_Z(b_mm, Zs, theta_x, theta_y) # Compute overlap area at each discrete depth 
    sigZ = depth_sigma_Z(b_mm, Zs, fl_pixels, sigma_d) # Compute depth uncertainty
    limit_workspace = np.where(sigZ <= sigmaZ_req, Aov, 0.0) # Only count overlap are where depth precision is acceptable
    V = np.trapezoid(limit_workspace, Zs) # Integrate across depth
    return V # Return volume


# ----- CALCULATIONS -----

# Focal length in pixels
fl_pixels = focal_length / pixel_pitch

# Sensor size (mm)
sensor_w = res_x * pixel_pitch
sensor_h = res_y * pixel_pitch

# FOV (radians)
# Getting FOV angle by using arctangent, where focal length is the adjacent side and one half of the sensor is the opposite side
theta_x = 2 * np.arctan(sensor_w / (2 * focal_length)) # Horizontal FOV angle
theta_y = 2 * np.arctan(sensor_h / (2 * focal_length)) # Vertical FOV angle

# Baseline sweep
b_sweep = np.linspace(b_min, b_max, num_samples)
V = np.array([resolvable_volume_for_baseline(bi) for bi in b_sweep])

# Get optimal baseline
b_opt = b_sweep[np.argmax(V)]
print("Optimal baseline (mm):", b_opt)
print("Max resolvable volume (mm^3):", V.max())

# Plot volume vs baseline
plt.figure()

# Main curve
line1, = plt.plot(b_sweep, V)

# Vertical line at optimal baseline
line2 = plt.axvline(
    b_opt,
    linestyle="--",
    linewidth=1,
    color="red",
    label=f"Optimal baseline = {b_opt:.1f} mm"
)

plt.xlabel("Baseline b (mm)")
plt.xlim(b_min, b_max)
plt.ylabel("Resolvable workspace volume (mm³)")
plt.grid(True)
plt.title(f"Resolvable workspace given minimum depth disparity requirement: {sigmaZ_req} mm")

plt.legend()
plt.show()