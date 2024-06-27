import os
import subprocess
import json


class GeolocationProcessor:
    def __init__(
        self, exiftool_path="exiftool"
    ):  # Allow customization of exiftool path
        self.exiftool_path = exiftool_path

    def get_geolocation(self, image_path):
        """Extracts geolocation data (latitude, longitude, altitude, references) from an image using exiftool."""
        command = [
            self.exiftool_path,
            "-json",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSAltitude",
            "-GPSLatitudeRef",
            "-GPSLongitudeRef",
            image_path,
        ]
        process = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        try:
            data = json.loads(process.stdout)[0]
            return (
                data.get("GPSLatitude"),
                data.get("GPSLongitude"),
                data.get("GPSAltitude"),
                data.get("GPSLatitudeRef"),
                data.get("GPSLongitudeRef"),
            )
        except (json.JSONDecodeError, IndexError):  # Catch potential errors
            return None, None, None, None, None

    def write_geolocation(
        self, dest_image, latitude, longitude, altitude, lat_ref, lon_ref
    ):
        """Writes geolocation data to an image using exiftool."""
        command = [
            self.exiftool_path,
            "-overwrite_original",
            f"-GPSLatitude={latitude}",
            f"-GPSLongitude={longitude}",
            f"-GPSAltitude={altitude}",
            f"-GPSLatitudeRef={lat_ref}",
            f"-GPSLongitudeRef={lon_ref}",
            dest_image,
        ]
        subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

    def process_image(self, raw_image_path, mask_image_path):
        """Copies geolocation information from the raw image to the mask image."""
        lat, lon, alt, lat_ref, lon_ref = self.get_geolocation(raw_image_path)

        if all((lat, lon, alt)):  # More concise check
            self.write_geolocation(mask_image_path, lat, lon, alt, lat_ref, lon_ref)
            print(f"Geolocation copied from {raw_image_path} to {mask_image_path}")
        else:
            print(f"No geolocation found in {raw_image_path}")


# if __name__ == "__main__":
#     processor = GeolocationProcessor()

#     # ... (Your code to get raw_image_path and mask_image_path) ...

#     processor.process_image(raw_image_path, mask_image_path)
