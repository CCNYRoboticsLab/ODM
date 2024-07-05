from opendm import io
from opendm import ai
from opendm.staindetection import StainDetector
from opendm.copy_geo_exiftool import GeolocationProcessor

from opendm import types
from opendm import log
from opendm import system
import os

# from opendm.concurrency import parallel_map

# from stages.dataset import valid_filename
# from stages.dataset import find_mask, get_images
from opendm import context
from opendm.photo import PhotoCorruptedException
from concurrent.futures import ThreadPoolExecutor, as_completed


class ODMStainSegmentationStage(types.ODM_Stage):
    def process(self, args, outputs):
        log.ODM_INFO("Running stain detection on images")

        # reconstruction = outputs["reconstruction"]
        # photos = reconstruction.photos
        outputs["start_time"] = system.now_raw()
        tree = types.ODM_Tree(args.project_path, args.gcp, args.geo, args.align)
        outputs["tree"] = tree

        if io.file_exists(tree.benchmarking):
            # Delete the previously made file
            try:
                os.remove(tree.benchmarking)
                with open(tree.benchmarking, "a") as b:
                    b.write(
                        "ODM Benchmarking file created %s\nNumber of Cores: %s\n\n"
                        % (system.now(), context.num_cores)
                    )
            except Exception as e:
                log.ODM_WARNING("Cannot write benchmark file: %s" % str(e))

        def valid_filename(filename, supported_extensions):
            (pathfn, ext) = os.path.splitext(filename)
            return ext.lower() in supported_extensions and pathfn[-5:] != "_mask"

        # Get supported images from dir
        def get_images(in_dir):
            entries = os.listdir(in_dir)
            valid, rejects = [], []
            for f in entries:
                if valid_filename(f, context.supported_extensions):
                    valid.append(f)
                else:
                    rejects.append(f)
            return valid, rejects

        def search_video_files(in_dir):
            entries = os.listdir(in_dir)
            return [
                os.path.join(in_dir, f)
                for f in entries
                if valid_filename(f, context.supported_video_extensions)
            ]

        def find_mask(photo_path, masks):
            (pathfn, ext) = os.path.splitext(os.path.basename(photo_path))
            k = "{}_mask".format(pathfn)

            mask = masks.get(k)
            if mask:
                # Spaces are not supported due to OpenSfM's mask_list.txt format reqs
                if not " " in mask:
                    return mask
                else:
                    log.ODM_WARNING(
                        "Image mask {} has a space. Spaces are currently not supported for image masks.".format(
                            mask
                        )
                    )

        images_dir = outputs["tree"].dataset_raw
        stain_overlay_dir = outputs["tree"].stain_overlay
        if not os.path.exists(stain_overlay_dir):
            system.mkdir_p(stain_overlay_dir)

        files, rejects = get_images(images_dir)
        if files:
            # create ODMPhoto list
            path_files = [os.path.join(images_dir, f) for f in files]

            # Lookup table for masks
            masks = {}
            for r in rejects:
                (p, ext) = os.path.splitext(r)
                if p[-5:] == "_mask" and ext.lower() in context.supported_extensions:
                    masks[p] = r

            photos = []
            with open(tree.dataset_list, "w") as dataset_list:
                log.ODM_INFO("Loading %s images" % len(path_files))
                for f in path_files:
                    try:
                        p = types.ODM_Photo(f)
                        p.set_mask(find_mask(f, masks))
                        photos.append(p)
                        dataset_list.write(photos[-1].filename + "\n")
                    except PhotoCorruptedException:
                        log.ODM_WARNING(
                            "%s seems corrupted and will not be used"
                            % os.path.basename(f)
                        )

        # Load stain detection model
        model = ai.get_model(
            "staindetection", "http://192.168.13.108:44289/config.json", "v1.0.0"
        )
        if model is None:
            log.ODM_WARNING(
                "Cannot load stain detection model. Skipping stain detection."
            )
            return

        stain_detector = StainDetector(model_path=model)
        geo_copier = GeolocationProcessor()

        def process_image(photo):
            input_image = os.path.join(images_dir, photo.filename)
            output_image = os.path.join(stain_overlay_dir, photo.filename)

            try:
                stain_detector.detect_and_overlay(input_image, output_image)
                log.ODM_INFO(f"Generated stain overlay for {photo.filename}")
                geo_copier.process_image(input_image, output_image)
                return output_image
            except Exception as e:
                log.ODM_WARNING(
                    f"Failed to generate stain overlay for {photo.filename}: {str(e)}"
                )
                # return None
                raise

        # overlay_images = parallel_map(
        #     process_image, photos, max_workers=args.max_concurrency
        # )

        def parallel_map(func, iterable, max_workers=None):
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(func, item): item for item in iterable}
                for future in as_completed(futures):
                    try:
                        yield future.result()
                    except Exception as e:
                        log.ODM_ERROR(f"Error processing {futures[future]}: {e}")

        overlay_images = list(
            parallel_map(process_image, photos, max_workers=args.max_concurrency)
        )

        # Filter out None values (failed detections)
        overlay_images = [img for img in overlay_images if img is not None]

        outputs["stain_overlay_images"] = overlay_images
        log.ODM_INFO(
            f"Completed stain detection. Generated {len(overlay_images)} overlay images."
        )
