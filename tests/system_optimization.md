# Stereo System Optimization

Our primary goal is to select the ideal lens for our system. To do so, we will, for a range of focus distances:

1. Calculate depth of field
2. Estimate pixel noise disparity
3. Using depth of field, and estimated pixel noise disparity, a stated maximum acceptable depth disparity, optimize baseline for total resolvable volume
 
We obtained the following sensor specifications from the camera documentation:

- $f_{mm}$ (focal length) = 3 mm
- $res_x$ (horizontal resolution) = 1600 pixels
- $res_y$ (vertical resolution) = 1200 pixels
- $d_p$ (pixel pitch) = 0.003 mm
- $N$ (aperture ratio) = 1.6

Set the following constraints for a range of possible baselines, with the minimum determined by the distance between camera pinholes if the chassis' of the cameras were touching, and maximum based on available space on Melt Stake arm:

- $b_{min}$ (minimum baseline) = 50 mm
- $b_{max}$ (maximum baseline) = 400 mm

--- 
## 1. Depth of field 


We calculated the depth of field to specify the extents of our workspace. We used the size of a pixel $d_p$ as the size of our circle of confusion $c$ which specified the required sharpness before a subject is considered "blurry". We obtained the hyperfocal distance by the following formula:

$$
H = \frac{f^2}{N c} + f
$$

Where:

- $f$ = focal length  
- $N$ = f-number (aperture ratio)  
- $c$ = circle of confusion 

Then, we calculated the near and far focus extents from the following formulae considering focus distance of the lens $s$:

Near Focus Distance:

$$
D_{\text{near}} = \frac{H s}{H + (s - f)}
$$

Far Focus Distance:

$$
D_{\text{far}} =
\begin{cases}
\infty, & s \ge H \\
\\
\frac{H s}{H - (s - f)}, & s < H
\end{cases}
$$

--- 
## 2. Noise induced pixel disparity

Given that the environment we're operating in has the possibility of being highly turbid and the effects of complex mixes of saline and freshwater on light attenuation, and used the Beer-Lambert Law for radiation beam attenuation for our model of noise induced pixel disparity as a function of depth, and selected a baseline standard deviation $\sigma_{b}$ $100$ mm: 

$$
\sigma_p(Z) = \sigma_{b} e^{\beta Z}
$$

Where:

- $\sigma_{b}$ = baseline disparity uncertainty at $Z = 100$
- $\beta$ = effective attenuation / degradation coefficient
- $Z$ = depth



---
## 3. Baseline optimization and resolvable volume

To optimize the baseline for maximum resolvable volume, we tested a number range of baselines, and included only overlapping regions that satisfied a maximum depth disparity $\sigma_{Z,\text{req}}$ of 0.5 mm to maintain millimeter resolution. For each possible baseline at a number of depths in our workspace range, the depth disparity was calculated by the stereo vision formula:

$$
\sigma_Z(Z) = \frac{Z^2}{f_{px} \, b} \, \sigma_{p}
$$

Where:

- $\sigma_{z}$ = depth disparity uncertainty at $Z$
- $\sigma_{p}$ = pixel disparity uncertainty at $Z$
- $f_{px}$ = focal length (pixels)
- $b$ = baseline


We also calculated the linear field of view at depth $Z$:

$$
W(Z) = 2 Z \tan\left(\frac{\theta_x}{2}\right)
$$

$$
H(Z) = 2 Z \tan\left(\frac{\theta_y}{2}\right)
$$

And the overlap:

$$
A_{ov}(Z) = W_{ov}(Z)\, H(Z)
$$

So we could calculate the effective area by:

$$
A_{\text{eff}}(Z) =
\begin{cases}
A_{ov}(Z), & \text{if } \sigma_Z(Z) \le \sigma_{Z,\text{req}} \\
0, & \text{otherwise}
\end{cases}
$$

And used the trapezoidal approximation rule to get our maximum resolvable volume:

$$
V(b) = \int_{Z_{\min}}^{Z_{\max}} A_{\text{eff}}(Z)\, dZ
$$

The optimal baseline is that which maximizes the resolvable volume: 
$$b_{opt} = arg\underset{b}maxV(b)
$$