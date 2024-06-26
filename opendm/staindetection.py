import cv2
import numpy as np
from opendm import log
from matplotlib import cm
import onnxruntime as ort


class StainDetector:  # Renamed the class
    def __init__(self, model_path):
        self.sess = ort.InferenceSession(model_path)
        self.input_name = self.sess.get_inputs()[0].name
        self.output_name = self.sess.get_outputs()[0].name

        input_shape = self.sess.get_inputs()[0].shape
        self.input_height, self.input_width = input_shape[2:]

    def detect_and_overlay(self, input_image, output_image):
        image = cv2.imread(input_image)
        if image is None:
            raise ValueError(f"Could not load image: {input_image}")

        preprocessed_image = self.preprocess(image)
        detections = self.detect_stains(preprocessed_image)
        overlay = self.create_overlay(image, detections)
        cv2.imwrite(output_image, overlay)

    def preprocess(self, image):
        img = cv2.resize(image, (self.input_width, self.input_height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)  # Transpose to CHW format
        img = img.reshape(1, *img.shape)
        return img

    def detect_stains(self, preprocessed_image):
        try:
            input_data = {self.input_name: preprocessed_image}
            out = self.sess.run([self.output_name], input_data)[0]

            segm_mask = np.argmax(out, axis=1)
            segm_mask = (segm_mask * 255 / segm_mask.max()).astype(np.uint8)
            segm_mask = np.squeeze(segm_mask, axis=0)

            return segm_mask
        except Exception as e:
            log.ODM_ERROR(f"Error during crack detection: {str(e)}")
            return []

    def create_overlay(self, original_image, segm_mask):
        original_height, original_width = original_image.shape[:2]
        resized_segm_mask = cv2.resize(
            segm_mask,
            (original_width, original_height),
            interpolation=cv2.INTER_NEAREST,
        )

        num_classes = segm_mask.max() + 1
        colormap = cm.get_cmap("viridis", num_classes)
        segm_mask_color = colormap(resized_segm_mask)[:, :, :3]
        segm_mask_color = (segm_mask_color * 255).astype(np.uint8)

        alpha = 0.5
        overlay_image = cv2.addWeighted(
            original_image, 1 - alpha, segm_mask_color, alpha, 0
        )

        return overlay_image
