import cv2
import numpy as np
from opendm import log
from matplotlib import cm


class CrackDetector:
    def __init__(self, model):
        # self.model = model
        # net = cv2.dnn.readNetFromONNX("your_model.onnx")
        net = cv2.dnn.readNetFromONNX(model)
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)  # Set backend to OpenCV
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)  # Set target to CPU
        net.enableWinograd(False)  # Disable Winograd
        self.net = net

    def detect_and_overlay(self, input_image, output_image):
        # Load the image
        image = cv2.imread(input_image)
        if image is None:
            raise ValueError(f"Could not load image: {input_image}")

        # Preprocess the image (resize, normalize, etc.)
        preprocessed_image = self.preprocess(image)

        # Run crack detection
        detections = self.detect_cracks(preprocessed_image)

        # Create overlay
        overlay = self.create_overlay(image, detections)

        # Save the overlay image
        cv2.imwrite(output_image, overlay)

    def preprocess(self, image):
        # Implement preprocessing steps here
        # This might include resizing, normalization, etc.
        # Example:
        # resized = cv2.resize(image, (512, 512))  # Resize to model input size
        # normalized = resized.astype(np.float32) / 255.0  # Normalize to [0, 1]
        # return normalized
        input_width = 512  # For ResNet-based models
        input_height = 512
        img = cv2.resize(img, (input_width, input_height))
        blob = cv2.dnn.blobFromImage(
            img, scalefactor=1.0 / 255, size=(input_width, input_height), swapRB=True
        )
        return blob

    def detect_cracks(self, preprocessed_image):
        # Run the crack detection model
        # This is a placeholder - replace with actual model inference
        try:
            # detections = self.model.predict(preprocessed_image)

            self.net.setInput(preprocessed_image)
            out = self.net.forward()

            segm_mask = np.argmax(out, axis=1)

            # Print information about the segmentation mask
            print(
                "Shape of segmentation mask:", segm_mask.shape
            )  # Should be (height, width) for single-channel
            print(
                "Data type of segmentation mask:", segm_mask.dtype
            )  # Should be np.uint8

            # Check the minimum and maximum values of the segmentation mask
            min_value = np.min(segm_mask)
            max_value = np.max(segm_mask)

            # Print minimum and maximum values for analysis
            print("Minimum value in the segmentation mask:", min_value)
            print("Maximum value in the segmentation mask:", max_value)
            # Convert segmentation mask to grayscale (0-255)
            segm_mask = (segm_mask * 255 / segm_mask.max()).astype(np.uint8)
            segm_mask = np.squeeze(segm_mask, axis=0)  # Remove the extra dimension here

            return segm_mask

            # return detections
        except Exception as e:
            log.ODM_ERROR(f"Error during crack detection: {str(e)}")
            return []

    def create_overlay(self, original_image, segm_mask):
        # overlay = original_image.copy()

        # # Draw detections on the overlay
        # for detection in detections:
        #     # Assuming each detection is [x, y, width, height, confidence]
        #     x, y, w, h, conf = detection

        #     # Convert to integer coordinates
        #     x, y, w, h = map(int, [x, y, w, h])

        #     # Draw rectangle
        #     cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)

        #     # Add confidence text
        #     text = f"{conf:.2f}"
        #     cv2.putText(
        #         overlay, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
        #     )

        # # Blend the overlay with the original image
        # alpha = 0.6  # Transparency factor
        # return cv2.addWeighted(overlay, alpha, original_image, 1 - alpha, 0)
        # Convert segmentation mask to grayscale (0-255) and squeeze
        original_height, original_width = original_image.shape[:2]
        # Resize the mask back to the original image dimensions
        resized_segm_mask = cv2.resize(
            segm_mask,
            (original_width, original_height),
            interpolation=cv2.INTER_NEAREST,
        )

        """
        Creates an overlay of the segmentation mask on top of the original image.

        Args:
            original_image: The original image (NumPy array).
            segm_mask: The segmentation mask (NumPy array).

        Returns:
            overlay_image: The image with the overlay applied.
        """
        # Apply a colormap to the segmentation mask
        num_classes = segm_mask.max() + 1
        colormap = cm.get_cmap("viridis", num_classes)  # Use 'viridis' colormap
        segm_mask_color = colormap(segm_mask)[
            :, :, :3
        ]  # Extract RGB channels (0-1 values)

        # Scale the colorized mask to 0-255
        segm_mask_color = (segm_mask_color * 255).astype(np.uint8)

        # Create an overlay with some transparency
        alpha = 0.5  # Adjust transparency as needed (0.0 = fully transparent, 1.0 = fully opaque)
        overlay_image = cv2.addWeighted(
            original_image, 1 - alpha, segm_mask_color, alpha, 0
        )

        return overlay_image
