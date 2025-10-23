import os
import time
import logging
from typing import Optional
try:
    from saleae import Saleae
except Exception:
    Saleae = None  # allow import to succeed even if saleae package unavailable

logger = logging.getLogger(__name__)

_saleae_instance: Optional[Saleae] = None

def create_saleae_instance(max_retries=3, retry_delay=2) -> Optional[Saleae]:
	"""
	Create a Saleae instance with automatic launch and retry mechanism.
	"""
	# Define all possible paths where Logic.exe might be installed
	common_paths = [
		os.path.expandvars(r"%ProgramFiles%\Saleae\Logic\Logic.exe"),
		os.path.expandvars(r"%ProgramFiles%\Logic\Logic.exe"),
		os.path.expandvars(r"%ProgramFiles(x86)%\Saleae\Logic\Logic.exe"),
		os.path.expanduser(r"~\AppData\Local\Programs\Saleae\Logic\Logic.exe")
	]

	# First, check if any of the paths exist
	saleae_path = None
	for path in common_paths:
		logger.info(f"Checking path: {path}")
		if os.path.exists(path):
			saleae_path = path
			logger.info(f"Found Saleae Logic at: {path}")
			# Check file permissions
			try:
				if os.access(path, os.R_OK):
					logger.info(f"File is readable: {path}")
				else:
					logger.warning(f"File exists but is not readable: {path}")
				if os.access(path, os.X_OK):
					logger.info(f"File is executable: {path}")
				else:
					logger.warning(f"File exists but is not executable: {path}")
			except Exception as e:
				logger.warning(f"Error checking file permissions: {str(e)}")
			break
		else:
			logger.info(f"Path does not exist: {path}")

	if saleae_path is None:
		logger.error("Saleae Logic software not found in common locations.")
		return None

	if Saleae is None:
		logger.error("python-saleae package not available (Saleae import failed).")
		return None

	for attempt in range(max_retries):
		try:
			# Try to create a new instance
			saleae = Saleae()
			# Test the connection
			saleae.get_connected_devices()
			return saleae
		except Exception as e:
			logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")

			if attempt < max_retries - 1:
				try:
					# Try to launch the software using the found path
					logger.info(f"Attempting to launch Saleae Logic from: {saleae_path}")
					# Try to launch using subprocess first
					try:
						import subprocess
						logger.info("Attempting to launch using subprocess...")
						subprocess.Popen([saleae_path])
						time.sleep(retry_delay)
					except Exception as subprocess_error:
						logger.warning(f"Subprocess launch failed: {str(subprocess_error)}")
						# Fall back to Saleae API launch
						saleae = Saleae()
						saleae.launch()

					# Wait for the software to start
					time.sleep(retry_delay)
				except Exception as launch_error:
					logger.error(f"Failed to launch Saleae Logic: {launch_error}")
					time.sleep(retry_delay)
					continue

	logger.error("Failed to connect to Saleae Logic after all attempts.")
	return None

def get_saleae() -> Optional[Saleae]:
	"""Return a cached Saleae instance, creating one if necessary."""
	global _saleae_instance
	if _saleae_instance is None:
		_saleae_instance = create_saleae_instance()
	return _saleae_instance
