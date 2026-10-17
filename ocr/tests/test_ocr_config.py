from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_ocr import _copy_models, _models_exist
from ocr_config import (
    DETECTION_MODEL_NAME,
    ENGLISH_RECOGNITION_MODEL_NAME,
    PASSPORT_RECOGNITION_MODEL_NAME,
    create_pipeline_settings,
    get_primary_profile,
    get_required_model_names,
)


class OcrConfigTest(unittest.TestCase):
    def test_selects_document_specific_models(self) -> None:
        passport_profile = get_primary_profile("passport")
        permit_profile = get_primary_profile("uaeResidencePermit")

        self.assertEqual(passport_profile.detection_model_name, DETECTION_MODEL_NAME)
        self.assertEqual(
            passport_profile.recognition_model_name,
            PASSPORT_RECOGNITION_MODEL_NAME,
        )
        self.assertEqual(
            permit_profile.recognition_model_name,
            ENGLISH_RECOGNITION_MODEL_NAME,
        )

    def test_disables_preprocessing_and_uses_bundled_paths(self) -> None:
        profile = get_primary_profile("passport")
        settings = create_pipeline_settings(profile, Path("models"))

        self.assertFalse(settings["use_doc_orientation_classify"])
        self.assertFalse(settings["use_doc_unwarping"])
        self.assertFalse(settings["use_textline_orientation"])
        self.assertEqual(
            settings["text_detection_model_dir"],
            str(Path("models") / DETECTION_MODEL_NAME),
        )
        self.assertEqual(
            settings["text_recognition_model_dir"],
            str(Path("models") / PASSPORT_RECOGNITION_MODEL_NAME),
        )

    def test_required_models_are_unique_and_copied_once(self) -> None:
        required_models = get_required_model_names()
        self.assertEqual(len(required_models), 3)
        self.assertEqual(len(required_models), len(set(required_models)))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "cache"
            output = root / "output"

            for model_name in required_models:
                model_directory = cache / model_name
                model_directory.mkdir(parents=True)
                (model_directory / "model.pdmodel").write_text(model_name)

            self.assertTrue(_models_exist(cache))
            _copy_models(cache, output)

            self.assertEqual(
                sorted(path.name for path in (output / "models").iterdir()),
                sorted(required_models),
            )

            (cache / required_models[0] / "model.pdmodel").unlink()
            (cache / required_models[0]).rmdir()
            self.assertFalse(_models_exist(cache))


if __name__ == "__main__":
    unittest.main()
