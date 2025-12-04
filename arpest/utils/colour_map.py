import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def add_colour_map():
    colors = [
        (0.00, "#003580"),   # deep blue
        (0.25, "#75BAF7"),   # light blue
        (0.45, "#FFFFFF"),   # white
        (0.65, "#F6E27F"),   # soft yellow
        (0.75, "#E3CA52"),   # warm yellow
        (0.90, "#A38C00"),   # darker golden yellow
        (1.00, "#A38C00"),   # flattened top -> smoothest result
    ]

    cmap_name = "arpest"
    cmap = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors)
    plt.register_cmap(cmap_name, cmap)