import cv2
import numpy as np
from opendm import log
import onnxruntime as ort

class StainDetector:
    def __init__(self, model_path):
        self.sess = ort.InferenceSession(model_path)
        self.input_name = self.sess.get_inputs()[0].name
        self.output_name = self.sess.get_outputs()[0].name
        input_shape = self.sess.get_inputs()[0].shape
        self.input_height, self.input_width = input_shape[2:]

    def detect_and_overlay(self, input_image, output_image, mask_output=None, alpha=0.5):
        """
        Detect stains in the input image, create a transparent overlay, and optionally save the mask.
        
        Args:
            input_image (str): Path to the input image file.
            output_image (str): Path to save the output overlay image.
            mask_output (str, optional): Path to save the mask image. If None, mask is not saved.
            alpha (float): Transparency level for the overlay (0.0 to 1.0).
        """
        image = cv2.imread(input_image)
        if image is None:
            raise ValueError(f"Could not load image: {input_image}")

        original_height, original_width = image.shape[:2]
        preprocessed_image = self._preprocess(image)
        detections = self._detect_stains(preprocessed_image, original_height, original_width)
        
        if mask_output:
            self._save_mask(detections, mask_output)
        
        overlay = self._create_overlay(image, detections, alpha)
        cv2.imwrite(output_image, overlay)

    def _preprocess(self, image):
        """Preprocess the input image for the ONNX model."""
        img = cv2.resize(image, (self.input_width, self.input_height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)  # Transpose to CHW format
        img = img.reshape(1, *img.shape)
        return img

    def _detect_stains(self, preprocessed_image, original_height, original_width):
        """Detect stains using the ONNX model and resize the mask to the original image size."""
        try:
            input_data = {self.input_name: preprocessed_image}
            out = self.sess.run([self.output_name], input_data)[0]
            segm_mask = np.argmax(out, axis=1)
            segm_mask = (segm_mask * 255 / segm_mask.max()).astype(np.uint8)
            segm_mask = np.squeeze(segm_mask, axis=0)
            
            # Resize the mask to match the original image dimensions
            resized_mask = cv2.resize(segm_mask, (original_width, original_height), interpolation=cv2.INTER_NEAREST)
            
            return resized_mask
        except Exception as e:
            log.ODM_ERROR(f"Error during stain detection: {str(e)}")
            return np.zeros((original_height, original_width), dtype=np.uint8)

    def _create_overlay(self, original_image, segm_mask, alpha=0.5):
        """Create a transparent overlay of the original image with detected stains."""
        # Create a red color mask for stains
        stain_mask = np.zeros_like(original_image)
        stain_mask[segm_mask > 0] = [0, 0, 255]  # Set red color for stains
        
        # Create the overlay using alpha blending
        overlay = cv2.addWeighted(original_image, 1, stain_mask, alpha, 0)
        
        return overlay

    def _save_mask(self, mask, output_path):
        """Save the segmentation mask as an image file."""
        cv2.imwrite(output_path, mask)

# Example usage
if __name__ == "__main__":
    model_path = "path/to/your/model.onnx"
    detector = StainDetector(model_path)
    
    input_image = "path/to/input/image.jpg"
    output_image = "path/to/output/overlay.jpg"
    mask_output = "path/to/output/mask.jpg"
    
    # You can adjust the alpha value (0.0 to 1.0) to control the transparency
    detector.detect_and_overlay(input_image, output_image, mask_output, alpha=0.5)