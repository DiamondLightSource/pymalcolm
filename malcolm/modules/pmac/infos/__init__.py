from .motorinfo import MotorInfo

# Expose all the classes
__all__ = sorted(k for k, v in globals().items() if type(v) == type)
