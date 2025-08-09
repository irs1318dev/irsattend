import cv2
import numpy as np

from .. import config


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
        resized_gray = cv2.resize(gray, (width * 2, height * 4), interpolation=cv2.INTER_LINEAR)
        
        resized_color = cv2.resize(frame, (width * 2, height * 4), interpolation=cv2.INTER_LINEAR)

        # Add more contrast
        _, threshed = cv2.threshold(resized_gray, 100, 255, cv2.THRESH_BINARY)

        # Create an output character grid
        output = ""
        braille_map = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))

        # Iterate over the image
        for y in range(0, threshed.shape[0], 4):
            for x in range(0, threshed.shape[1], 2):
                char_code = 0x2800
                for row in range(4):
                    for col in range(2):
                        if y + row < threshed.shape[0] and x + col < threshed.shape[1]:
                            if threshed[y + row, x + col] > 0:
                                char_code |= braille_map[row][col]
                
                # Get the average color for this block
                block_b, block_g, block_r = 0, 0, 0
                pixel_count = 0
                for row in range(4):
                    for col in range(2):
                        if y + row < resized_color.shape[0] and x + col < resized_color.shape[1]:
                            b, g, r = resized_color[y + row, x + col]
                            block_b += int(b)
                            block_g += int(g) 
                            block_r += int(r)
                            pixel_count += 1
                
                if pixel_count > 0:
                    avg_b = block_b // pixel_count
                    avg_g = block_g // pixel_count
                    avg_r = block_r // pixel_count
                    
                    # Add more brightness
                    avg_r = min(255, int(avg_r * 1.3))
                    avg_g = min(255, int(avg_g * 1.3))
                    avg_b = min(255, int(avg_b * 1.3))
                    
                    rgb_color = f"rgb({avg_r},{avg_g},{avg_b})"
                    braille_char = chr(char_code)
                    colored_char = f"[{rgb_color}]{braille_char}[/{rgb_color}]"
                    output += colored_char
                else:
                    output += chr(char_code)
            output += "\n"
        return output
