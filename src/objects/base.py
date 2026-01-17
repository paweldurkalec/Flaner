class CanvasObject:
    """Base class for drawable objects tied to the original image coordinates."""
    def draw(self, surface, image_rect, image_scale, font):
        raise NotImplementedError()

    def to_dict(self):
        return {}
