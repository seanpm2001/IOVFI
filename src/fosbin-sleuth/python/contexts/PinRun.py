import os
from .binaryutils import log
import subprocess


class PinRun:
    def __init__(self, pin_loc, pintool_loc, binary_loc, target, loader_loc=None):
        self.return_code = None
        self.in_contexts = None
        self.out_contexts = None
        self.binary = os.path.abspath(binary_loc)
        self.completed_proc = None
        self.process_timedout = None

        try:
            self.target = hex(int(target, 16))
        except Exception:
            self.target = target

        self.pin_loc = os.path.abspath(pin_loc)
        self.pintool_loc = os.path.abspath(pintool_loc)
        self.watchdog = None
        self.fuzz_count = None
        self.log_loc = None
        if loader_loc is not None:
            self.loader_loc = os.path.abspath(loader_loc)

    def _check_state(self):
        if self.pin_loc is None:
            raise ValueError("pin_loc is None")
        if self.pintool_loc is None:
            raise ValueError("pintool_loc is None")
        if self.binary_loc is None:
            raise ValueError("binary_loc is None")
        if self.target is None:
            raise ValueError("function is None")
        if os.path.splitext(self.binary_loc)[1] == ".so" and self.loader_loc is None:
            raise ValueError("loader_loc is None")

    def generate_cmd(self):
        cmd = [self.pin_loc, "-t", self.pintool_loc]

        if self.fuzz_count is not None:
            cmd.append("-fuzz-count")
            cmd.append(str(self.fuzz_count))

        if self.watchdog is not None:
            cmd.append("-watchdog")
            cmd.append(str(self.watchdog))

        if self.log_loc is not None:
            cmd.append("-out")
            cmd.append(os.path.abspath(self.log_loc))

        if self.in_contexts is not None:
            cmd.append("-contexts")
            cmd.append(self.in_contexts)

        if self.out_contexts is not None:
            cmd.append("-ctx-out")
            cmd.append(os.path.abspath(self.out_contexts))

        if os.path.splitext(self.binary_loc)[1] == ".so":
            cmd.append("-shared-func")
        else:
            cmd.append("-target")

        cmd.append(self.target)
        cmd.append("--")

        if os.path.splitext(self.binary_loc)[1] == ".so":
            cmd.append(self.loader_loc)
            cmd.append(self.binary)
        else:
            cmd.append(self.binary)

        return cmd

    def execute_cmd(self, cwd=os.getcwd(), capture_out=False):
        self._check_state()
        cmd = self.generate_cmd()
        if self.watchdog is not None:
            timeout = int(self.watchdog) / 1000 + 1
        else:
            timeout = 0
        log.info("Running {}".format(" ".join(cmd)))

        try:
            self.completed_proc = subprocess.run(cmd, timeout=timeout, cwd=os.path.abspath(cwd),
                                                 capture_output=capture_out)
            self.process_timedout = False
        except subprocess.TimeoutExpired as e:
            self.process_timedout = True
            raise e

    def returncode(self):
        if self.completed_proc is not None:
            return self.completed_proc.returncode
        return None
