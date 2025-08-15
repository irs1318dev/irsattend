import cv2
import numpy as np

from irsattend import config


class Camera:
    def __init__(self, camera_index=config.CAMERA_NUMBER, width=640, height=480):
        """Initialize the camera."""
        # Initialize the camera and set its resolution
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open camera at index {camera_index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        """Get a frame from the camera."""
        ret, frame = self.cap.read()
        if ret and frame is not None:
            # Mirror the camera so it looks natural
            frame = cv2.flip(frame, 1)
        return ret, frame

    def release(self):
        """Releases the camera."""
        self.cap.release()

    @staticmethod
    def frame_to_braille(frame: np.ndarray, width: int, height: int) -> str:
        """
        Algorithm to convert a frame to braille characters for display.
        In case we dont do separate camera window
        """
        # Convert to grayscale and resize
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized_gray = cv2.resize(
            gray, (width * 2, height * 4), interpolation=cv2.INTER_NEAREST
        )

        resized_color = cv2.resize(
            frame, (width * 2, height * 4), interpolation=cv2.INTER_NEAREST
        )

        # Add more contrast
        _, threshed = cv2.threshold(resized_gray, 100, 255, cv2.THRESH_BINARY)

        # Create an output character grid
        output = ""
        braille_map = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))

        color_blocks = {}

        # Iterate over the image
        for y in range(0, threshed.shape[0], 4):
            for x in range(0, threshed.shape[1], 2):
                char_code = 0x2800
                for row in range(4):
                    for col in range(2):
                        if y + row < threshed.shape[0] and x + col < threshed.shape[1]:
                            if threshed[y + row, x + col] > 0:
                                char_code |= braille_map[row][col]

                block_key = (y, x)
                if block_key not in color_blocks:
                    y_end = min(y + 4, resized_color.shape[0])
                    x_end = min(x + 2, resized_color.shape[1])
                    color_block = resized_color[y:y_end, x:x_end]

                    if color_block.size > 0:
                        avg_color = np.mean(color_block.reshape(-1, 3), axis=0)
                        avg_b, avg_g, avg_r = avg_color.astype(int)

                        # Add more brightness
                        avg_r = min(255, int(avg_r * 1.3))
                        avg_g = min(255, int(avg_g * 1.3))
                        avg_b = min(255, int(avg_b * 1.3))

                        color_blocks[block_key] = f"rgb({avg_r},{avg_g},{avg_b})"
                    else:
                        color_blocks[block_key] = None

                if color_blocks[block_key]:
                    rgb_color = color_blocks[block_key]
                    braille_char = chr(char_code)
                    colored_char = f"[{rgb_color}]{braille_char}[/{rgb_color}]"
                    output += colored_char
                else:
                    output += chr(char_code)
            output += "\n"
        return output

    @staticmethod
    def calculate_preview_size(container_size) -> tuple[int, int]:
        """Calculate preview dimensions based on container size"""

        # Get container dimensions
        container_width = container_size.width if container_size.width > 0 else 100
        container_height = container_size.height if container_size.height > 0 else 30

        # Use most of the container but leave some padding
        available_width = max(int(container_width * 0.9), 40)
        available_height = max(int(container_height * 0.9), 20)

        target_aspect_ratio = 3.0

        if available_width / target_aspect_ratio <= available_height:
            preview_width = available_width
            preview_height = max(int(available_width / target_aspect_ratio), 15)
        else:
            preview_height = available_height
            preview_width = max(int(available_height * target_aspect_ratio), 40)

        preview_width = min(preview_width, container_width - 2)
        preview_height = min(preview_height, container_height - 2)

        preview_width = max(min(preview_width, 200), 40)
        preview_height = max(min(preview_height, 60), 15)

        return preview_width, preview_height
