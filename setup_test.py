import unittest
import setup


def run_cmd_mock(cmd, return_code=False, shell=False, command_result_dict={}):
    return command_result_dict[cmd]


class TestMathOperations(unittest.TestCase):

    def setUp(self):
        self.prev_run_cmd = setup.run_cmd

    def _set_run_cmd(self, result_map):
        cmd = lambda **kwargs: run_cmd_mock(command_result_dict=result_map,
                                            **kwargs)
        setup.run_cmd = cmd

    def tearDown(self):
        setup.run_cmd = self.prev_run_cmd

    def test_release_tag(self):
        self._set_run_cmd({
            "git rev-parse --abbrev-ref HEAD": "v0.3.0-dev",
            "git tag --points-at HEAD": "v0.3.14"
        })
        version = setup.get_git_version()
        self.assertEqual(version, "0.3.14")

    def test_release_branch_dev0(self):
        self._set_run_cmd({
            "git rev-parse --abbrev-ref HEAD": "v0.3.0-dev",
            "git tag --points-at HEAD": "",
            "git describe --tags --match v0.3.* --abbrev=0": ("", "", 128)
        })
        version = setup.get_git_version()
        self.assertEqual(version, f"0.3.0.dev{setup.today}")

    def test_release_branch_dev3(self):
        self._set_run_cmd({
            "git rev-parse --abbrev-ref HEAD": "v0.3.0-dev",
            "git tag --points-at HEAD": "",
            "git describe --tags --match v0.3.* --abbrev=0": ("v0.3.2", "", 0)
        })
        version = setup.get_git_version()
        self.assertEqual(version, f"0.3.3.dev{setup.today}")

    def test_release_branch_dev_unkown_tag(self):
        self._set_run_cmd({
            "git rev-parse --abbrev-ref HEAD": "v0.3.0-dev",
            "git tag --points-at HEAD": "",
            "git describe --tags --match v0.3.* --abbrev=0": ("v0.3.0-dev0", "", 0)
        })
        version = setup.get_git_version()
        self.assertEqual(version, f"0.3.0.dev{setup.today}")

    def test_feature_branch(self):
        self._set_run_cmd({
            "git rev-parse --abbrev-ref HEAD": "ref-GUI4US-1",
            "git tag --points-at HEAD": "",
            "git log --reverse --abbrev-commit --format=%P": "123",
            "git branch --contains 123": "v0.3.0-dev",
            "git describe --tags --match v0.3.* --abbrev=0": ("", "", 128)
        })
        version = setup.get_git_version()
        self.assertEqual(version, f"0.3.0.dev{setup.today}+ref.gui4us.1")


if __name__ == '__main__':
    unittest.main()