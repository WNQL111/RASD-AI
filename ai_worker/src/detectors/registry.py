import logging

logger = logging.getLogger(__name__)

class PortableObjectRegistry:
    """
    Extensible Registry for portable objects monitored for potential theft.
    Maps coco class IDs to human-readable names.
    """
    # Default COCO classes for portable objects
    _registry = {
        24: "backpack",
        25: "umbrella",
        26: "handbag",
        28: "suitcase",
        39: "bottle",
        40: "wine glass",
        41: "cup",
        63: "laptop",
        64: "mouse",
        65: "keyboard",
        66: "cell phone",
        67: "cell phone",
        73: "book",
        74: "clock"
    }

    @classmethod
    def register(cls, class_id: int, name: str):
        """Allows dynamic registration of custom objects without code modifications."""
        cls._registry[class_id] = name
        logger.info(f"Registered new portable object class {class_id} as '{name}'")

    @classmethod
    def get_registered_classes(cls) -> list:
        return list(cls._registry.keys())

    @classmethod
    def get_item_name(cls, class_id: int) -> str:
        return cls._registry.get(class_id, "object")
