import numpy as np
from scanpointgenerator import Point


def make_gaussian_blob(width, height):
    """Make a Gaussian Blob with float values in range 0..1"""
    x, y = np.meshgrid(np.linspace(-1, 1, width), np.linspace(-1, 1, height))
    d = np.sqrt(x * x + y * y)
    blob = np.exp(-(d ** 2))
    return blob


def interesting_pattern(point: Point) -> float:
    """This function is interesting in x and y in range -10..10. Given a Point,
    use the x and y values contained in it to make a float value in range 0..1
    """
    names = sorted(point.positions)
    # See if we are scanning x vs y
    x_names = [k for k in names if "x" in k.lower()]
    y_names = [k for k in names if "y" in k.lower()]
    if x_names and y_names:
        # If we are then use them
        x = point.positions[x_names[0]]
        y = point.positions[y_names[0]]
    elif names:
        # Otherwise use what we have
        x = point.positions[names[0]]
        y = point.positions[names[-1]]
    else:
        # No points, make something up
        x = 0
        y = 0
    # Return a value between 0 and 1 based on a function that gives interesting
    # pattern on x and y in range -10:10
    z = 0.5 + (np.sin(x) ** 10 + np.cos(10 + y * x) * np.cos(x)) / 2
    return z
