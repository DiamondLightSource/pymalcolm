import numpy as np

from scanpointgenerator import Point


def make_gaussian_blob(width, height):
    """Make a Gaussian Blob with float values in range 0..1"""
    x, y = np.meshgrid(np.linspace(-1, 1, width), np.linspace(-1, 1, height))
    d = np.sqrt(x*x+y*y)
    blob = np.exp(-d**2)
    return blob


def interesting_pattern(point):
    # type: (Point) -> float
    """This function is interesting in x and y in range -10..10. Given a Point,
    use the x and y values contained in it to make a float value in range 0..1
    """
    # Grab the x and y values out of the point
    x = [v for k, v in sorted(point.positions.items()) if "x" in k.lower()][0]
    y = [v for k, v in sorted(point.positions.items()) if "y" in k.lower()][0]
    # Return a value between 0 and 1 based on a function that gives interesting
    # pattern on x and y in range -10:10
    z = 0.5 + (np.sin(x)**10 + np.cos(10 + y*x) * np.cos(x))/2
    return z