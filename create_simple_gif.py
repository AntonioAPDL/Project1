import numpy as np
import matplotlib.pyplot as plt
import imageio

def create_frames(image_path, n_frames=50):
    image = imageio.imread(image_path)
    frames = []
    for i in range(n_frames):
        # Example transformation: Change brightness
        frame = np.clip(image * (1 + 0.1 * np.sin(2 * np.pi * i / n_frames)), 0, 255).astype(np.uint8)
        frames.append(frame)
    return frames

def generate_gif(image_path, output_gif, n_frames=50):
    frames = create_frames(image_path, n_frames)
    imageio.mimsave(output_gif, frames, duration=0.1)

if __name__ == "__main__":
    generate_gif('/home/jaguir26/project1_ucsc_phd/stats_logo.png', '/home/jaguir26/project1_ucsc_phd/stats_logo.gif')


