import logging

logger = logging.getLogger(__name__)

def is_point_in_polygon(x, y, poly):
    num = len(poly)
    if num < 3:
        return False
    j = num - 1
    c = False
    for i in range(num):
        if ((poly[i][1] > y) != (poly[j][1] > y)) and \
           (x < (poly[j][0] - poly[i][0]) * (y - poly[i][1]) / max(1e-5, (poly[j][1] - poly[i][1])) + poly[i][0]):
            c = not c
        j = i
    return c

class ZoneEngine:
    """
    Evaluates whether tracked objects are within user-defined security zones
    (Safe, Restricted, VIP, Entrance, Cashier, etc.) and adjusts alert risk factors.
    """
    def __init__(self, zones_list=None):
        self.zones = zones_list or []

    def get_point_zones(self, x, y):
        """Returns all matching zones for a 2D coordinate."""
        matched = []
        for zone in self.zones:
            poly = zone.get("points", [])
            if poly and is_point_in_polygon(x, y, poly):
                matched.append(zone)
        return matched

    def get_bbox_zones(self, bbox):
        """Checks if bottom-center of bbox (feet position) is in any zone."""
        x_center = (bbox[0] + bbox[2]) / 2.0
        y_bottom = bbox[3]
        return self.get_point_zones(x_center, y_bottom)
