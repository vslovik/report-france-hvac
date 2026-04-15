import numpy as np
import pandas as pd


def plot_median_band(ax, values, color, label):
    """
    This function plots a median line with an inter quartile range (IQR) shaded
    band across multiple variable-length sequences.

    Given many runs of some recorded metric (e.g. training loss curves of different lengths),
    it plots the median trajectory with a shaded IQR band showing spread —
    a common visualization for comparing noisy experimental results.
    """

    # Padding
    # values is a list of lists that may have different lengths. Each shorter
    # list is padded to max_len by repeating its last value — a "hold last value" strategy.
    max_len = max(len(c) for c in values)
    padded = [c + [c[-1]] * (max_len - len(c)) for c in values]

    # Aggregation
    # It stacks all sequences into a 2D array and computes column-wise statistics: the median
    # (50th percentile), lower quartile (25th), and upper quartile (75th).
    arr = np.array(padded)
    median = np.median(arr, axis=0)
    lo = np.percentile(arr, 25, axis=0)
    hi = np.percentile(arr, 75, axis=0)

    # Plotting
    # It draws the median as a solid line, then fills the area between the 25th and 75th percentiles
    # with a semi-transparent band (alpha=0.15) of the same color.
    keys = range(max_len)
    ax.plot(keys, median, color=color, linewidth=2, label=label)
    ax.fill_between(keys, lo, hi, color=color, alpha=0.15)

