import math

def hav(x):
    a = math.sin(0.5 * x)
    return a * a

def distance(a, b, r=3958.8):
    a_lat = math.radians(a[0])
    a_long = math.radians(a[1])
    b_lat = math.radians(b[0])
    b_long = math.radians(b[1])
    
    return 2*r * math.asin(math.sqrt(hav(b_lat - a_lat) + (math.cos(a_lat) * math.cos(b_lat) * hav(b_long - a_long))))