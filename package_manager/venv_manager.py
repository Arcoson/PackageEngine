import os
import venv
from .utils import setup_logger

logger = setup_logger()

class VenvManager:
    def create_venv(self, venv_name):
        """Create a new virtual environment"""
        try:
            venv_path = os.path.abspath(venv_name)
            
            if os.path.exists(venv_path):
                raise Exception(f"Virtual environment '{venv_name}' already exists")
            
            builder = venv.EnvBuilder(
                system_site_packages=False,
                clear=True,
                symlinks=True,
                upgrade=False,
                with_pip=True
            )
            
            builder.create(venv_path)
            
            # Print activation instructions
            logger.info(f"Virtual environment created successfully at: {venv_path}")
            logger.info("\nTo activate the virtual environment:")
            logger.info(f"  Windows: {venv_path}\\Scripts\\activate")
            logger.info(f"  Unix/MacOS: source {venv_path}/bin/activate")
            
        except Exception as e:
            raise Exception(f"Failed to create virtual environment: {str(e)}")
