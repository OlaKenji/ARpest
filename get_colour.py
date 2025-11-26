import matplotlib.pyplot as plt
import numpy as np

# Create a figure and axis to display the colormap
fig, ax = plt.subplots(figsize=(6, 1))

# Create a colormap object using the name 'terrain'
cmap = plt.get_cmap('RdYlBu_r')

# Display the colormap
cbar = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap),
                    cax=ax, orientation='horizontal')

# Show the plot
plt.show()

# Now, let's sample colors from the colormap to create a custom colormap
num_colors = 10  # Number of colors to sample

terrain_colors = [cmap(i / (num_colors - 1)) for i in range(num_colors)]

# Print the sampled colors
print(terrain_colors)