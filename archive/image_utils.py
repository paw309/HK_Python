import os
import pygame
import random

def load_all_flag_icons(flag_dir):
    """
    Loads all flag png images from the given directory into a dictionary.
    Key: color name (as filename part after 'flag_' and before '.png')
    Value: loaded pygame.Surface
    Returns: dict: { 'red': Surface, 'blue': Surface, ... }
    """
    flag_icons = {}
    # Accept both 'flag_color.png' and optionally 'flag_colorX.png'
    for fname in os.listdir(flag_dir):
        if fname.startswith('flag_') and fname.endswith('.png'):
            color = fname[len('flag_'):-4]  # Extract 'red', 'blue', etc
            path = os.path.join(flag_dir, fname)
            icon = pygame.image.load(path).convert_alpha()
            flag_icons[color] = icon
    return flag_icons

def pick_random_flag_color(flag_icons, exclude=('white', 'gray', 'black')):
    """
    Picks a single random color (except excluded) and returns the Surface.
    """
    eligible = [c for c in flag_icons if c not in exclude]
    chosen_color = random.choice(eligible)
    return chosen_color, flag_icons[chosen_color]

def pick_random_flag_color_list(flag_icons, num_flags, exclude=('white', 'gray', 'black')):
    """
    Returns a randomized color list of length num_flags, cycling if needed (except excluded).
    Returns: [ ('green', Surface), ('orange', Surface), ... ] (ordinal order)
    """
    eligible = [c for c in flag_icons if c not in exclude]
    random.shuffle(eligible)
    # Cycle colors if not enough for all flags
    color_list = []
    for i in range(num_flags):
        color = eligible[i % len(eligible)]
        color_list.append( (color, flag_icons[color]) )
    return color_list

# ---- Usage Example ----
# In your main() or game setup:
# flag_dir = os.path.join("Hamiltonian-Knights", "assets", "flags")
# flag_icons = load_all_flag_icons(flag_dir)
#
# # To pick a single color for all flags:
# colorname, flag_icon = pick_random_flag_color(flag_icons)
# # Use flag_icon for all flag overlays
#
# # To assign colors to each flag in ordinal order (cycled as needed):
# num_flags = 10
# flag_colors = pick_random_flag_color_list(flag_icons, num_flags)
# # flag_colors[ordinal-1][1] is the Surface for flag ordinal 1, etc.
