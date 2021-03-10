import shutil
import tempfile
from pathlib import Path

from sync import determine_actions, sync


class TestE2E:
    @staticmethod
    def test_when_a_file_exists_in_the_source_but_not_the_destination():
        try:
            source = tempfile.mkdtemp()
            dest = tempfile.mkdtemp()

            # Create a new file in source
            content = "I am a test document"
            (Path(source) / "my-file").write_text(content)

            # Test our composed method
            sync(source, dest)

            # Test that the correct destination has been created
            expected_path = Path(dest) / "my-file"
            assert expected_path.exists()
            # .. and that the contents are the same
            assert expected_path.read_text() == content
        finally:
            shutil.rmtree(source)
            shutil.rmtree(dest)

    @staticmethod
    def test_when_a_file_has_been_renamed_in_the_source():
        try:
            source = tempfile.mkdtemp()
            dest = tempfile.mkdtemp()

            # Create a new file in source
            content = "I am a test document"
            # Latest name in source
            latest_source_path = Path(source) / "latest_filename"
            # Original name saved to dest
            old_dest_path = Path(dest) / "dest_filename"
            # After sync'ing the destination should match source
            expected_latest_dest_path = Path(dest) / "latest_filename"
            latest_source_path.write_text(content)
            old_dest_path.write_text(content)

            sync(source, dest)

            # Check that the old path no longer exists
            assert old_dest_path.exists() is False
            # Check that the same content has been carried over to the latest dest path
            assert expected_latest_dest_path.read_text() == content

        finally:
            shutil.rmtree(source)
            shutil.rmtree(dest)


def test_when_a_file_exists_in_the_source_but_not_in_the_destination():
    src_hashes = {"hash1": "fn1"}
    dst_hashes = {}
    actions = determine_actions(src_hashes, dst_hashes, "/src", "/dst")
    assert list(actions) == [("copy", Path("/src/fn1"), Path("/dst/fn1"))]


def test_when_a_file_has_been_renamed_in_the_source():
    src_hashes = {"hash1": "fn_renamed"}
    dst_hashes = {"hash1": "fn1"}
    actions = determine_actions(src_hashes, dst_hashes, "/src", "/dst")
    assert list(actions) == [("move", Path("/dst/fn1"), Path("/dst/fn_renamed"))]
