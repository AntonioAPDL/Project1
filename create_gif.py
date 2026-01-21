import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from emcee import EnsembleSampler
from tqdm import tqdm
import os

# Function to progressively update the image with color gradients
def update_image(image, samples, current_image, step, nsteps):
    alpha = step / nsteps
    for i in range(samples.shape[0]):
        x, y = samples[i]
        x = int(np.round(x))
        y = int(np.round(y))
        if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
            current_image[y, x] = alpha * image[y, x] + (1 - alpha) * current_image[y, x]
    return current_image

# Function to sample points from the image based on intensity
def log_prob(coords, image, max_intensity):
    x, y = coords
    if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
        intensity = np.sum(image[int(y), int(x)]) / max_intensity
        return intensity  # Higher intensity (darker pixels) gets higher log_prob
    return -np.inf

# Create the frames directory
frames_dir = "frames"
if not os.path.exists(frames_dir):
    os.makedirs(frames_dir)

# Load the image
image_path = "stats_logo.png"
image = imageio.imread(image_path)

# Normalize image intensity
max_intensity = np.max(image)

# Initialize walkers
nwalkers = 500
ndim = 2
initial_positions = np.random.rand(nwalkers, ndim) * np.array([image.shape[1], image.shape[0]])

# Set up the sampler
sampler = EnsembleSampler(nwalkers, ndim, log_prob, args=[image, max_intensity])

# Initialize the current image as a blank canvas with transparency
current_image = np.zeros_like(image)

# Sample and update image frames
nsteps = 5000
for step in tqdm(range(nsteps)):
    sampler.run_mcmc(initial_positions, 1, progress=False)
    initial_positions = sampler.get_last_sample().coords
    current_image = update_image(image, initial_positions, current_image, step, nsteps)
    plt.imsave(f"frames/frame_{step:03d}.png", current_image, format='png')

# Create the GIF
frame_paths = [os.path.join(frames_dir, f"frame_{i:03d}.png") for i in range(nsteps)]
frames = [imageio.imread(frame_path) for frame_path in frame_paths]
imageio.mimsave("output.gif", frames, duration=0.1)  # Set the duration to 0.05 seconds per frame
