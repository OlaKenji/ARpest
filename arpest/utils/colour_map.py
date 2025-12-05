import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def add_colour_map():
    colors = [
        (0.00, "#00255E"),  # very dark blue
        (0.08, "#0E4A9B"),  # deep blue
        (0.22, "#5CA8E6"),  # mid-blue
        (0.42, "#D2EDFF"),  # barely blue-white
        (0.50, "#FFFFFF"),  # center peak
        (0.58, "#FFF7D7"),  # slightly yellowish white
        (0.72, "#E8D56F"),  # light yellow
        (0.88, "#C8B03B"),  # mid-yellow
        (1.00, "#9C8200"),  # darker golden yellow
    ]

    cmap_name = "arpest"
    cmap = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors)
    plt.register_cmap(cmap_name, cmap)


#colors = [
#    (0.00, "#003580"),   # deep blue
#    (0.25, "#75BAF7"),   # light blue
#    (0.45, "#FFFFFF"),   # white
#    (0.65, "#F6E27F"),   # soft yellow
#    (0.75, "#E3CA52"),   # warm yellow
#    (0.90, "#C4B454"),   # darker golden yellow
#    (1.00, "#A38C00"),   # flattened top -> smoothest result
#]    