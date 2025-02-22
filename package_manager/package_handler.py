import json
import os
import subprocess
import concurrent.futures
from datetime import datetime
from tqdm import tqdm
import hashlib
import requests
from packaging import version
from .utils import setup_logger

logger = setup_logger()

class PackageEngine:
    def __init__(self):
        self.packages_file = "packages.json"
        self.cache_dir = os.path.join(os.getcwd(), ".pkgx_cache")
        self._init_dirs()

    def _init_dirs(self):
        if not os.path.exists(self.packages_file):
            with open(self.packages_file, 'w') as f:
                json.dump({"packages": {}}, f)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _load_packages(self):
        try:
            with open(self.packages_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Error loading packages file: {str(e)}")
            return {"packages": {}}

    def _save_packages(self, data):
        try:
            with open(self.packages_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving packages file: {str(e)}")
            raise

    def _parse_package_spec(self, package_spec):
        if "==" in package_spec:
            name, version = package_spec.split("==")
            return name.strip(), version.strip()
        return package_spec.strip(), None

    def _get_base_name(self, package_spec):
        """Extract base package name without version specifiers"""
        name = package_spec.split(";")[0].split("[")[0].split("(")[0].strip()
        return name.split("<")[0].split(">")[0].split("=")[0].strip()

    def _get_dependencies(self, package_name):
        try:
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                requires_dist = data["info"].get("requires_dist", [])
                if requires_dist is None:
                    return []

                dependencies = []
                for req in requires_dist:
                    if req and "extra ==" not in req:  # Skip optional dependencies
                        dep_name = self._get_base_name(req)
                        if dep_name and dep_name not in dependencies:
                            dependencies.append(dep_name)
                return dependencies
            return []
        except Exception as e:
            logger.debug(f"Error fetching dependencies for {package_name}: {str(e)}")
            return []

    def _check_package_security(self, package_name):
        try:
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                releases = data.get("releases", {})
                if releases:
                    latest_version = max(releases.keys(), key=lambda x: version.parse(x))
                    release_data = releases[latest_version][0]
                    package_hash = release_data.get("digests", {}).get("sha256")
                    return package_hash
        except Exception as e:
            logger.debug(f"Error checking security for {package_name}: {str(e)}")
            return None
        return None

    def _get_installed_version(self, package_name):
        try:
            base_name = self._get_base_name(package_name)
            result = subprocess.check_output(["pip", "show", base_name]).decode()
            for line in result.split("\n"):
                if line.startswith("Version: "):
                    return line.split(": ")[1].strip()
            return None
        except Exception as e:
            logger.debug(f"Error getting version for {base_name}: {str(e)}")
            return None

    def _get_package_metadata(self, package_name):
        try:
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                info = data["info"]
                return {
                    "author": info.get("author") or "Unknown",
                    "license": info.get("license") or "Unknown",
                    "summary": info.get("summary") or "No description available"
                }
            return None
        except Exception as e:
            logger.debug(f"Error fetching metadata for {package_name}: {str(e)}")
            return None

    def _get_latest_version(self, package_name):
        """Get the latest version available on PyPI"""
        try:
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                releases = data.get("releases", {}).keys()
                if releases:
                    # Filter out pre-releases unless only pre-releases exist
                    stable_releases = [r for r in releases if not version.parse(r).is_prerelease]
                    if stable_releases:
                        return max(stable_releases, key=lambda x: version.parse(x))
                    return max(releases, key=lambda x: version.parse(x))
            return None
        except Exception as e:
            logger.debug(f"Error fetching latest version for {package_name}: {str(e)}")
            return None

    def install_package(self, package_spec):
        base_name = self._get_base_name(package_spec)
        try:
            cmd = ["pip", "install", "--user", "--cache-dir", self.cache_dir, package_spec]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            with tqdm(total=100, desc=f"Installing {base_name}", position=0, leave=True) as pbar:
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        if "Collecting" in output:
                            pbar.update(20)
                        elif "Downloading" in output:
                            pbar.update(30)
                        elif "Installing" in output:
                            pbar.update(40)
                        elif "Successfully" in output:
                            pbar.update(10)

            if process.returncode != 0:
                stderr = process.stderr.read()
                if "externally-managed-environment" in stderr:
                    cmd.append("--break-system-packages")
                    subprocess.check_call(cmd)
                else:
                    raise Exception(f"Installation failed: {stderr}")

            installed_version = self._get_installed_version(base_name)
            if not installed_version:
                raise Exception(f"Could not determine version for {base_name}")

            data = self._load_packages()
            data["packages"][base_name] = {
                "version": installed_version,
                "install_date": datetime.now().isoformat(),
                "security_hash": self._check_package_security(base_name)
            }

            self._save_packages(data)
            logger.info(f"✓ {base_name}=={installed_version} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install {base_name}: {str(e)}")
            return False

    def install_multiple(self, package_specs):
        all_packages = set()
        for spec in package_specs:
            name = self._get_base_name(spec)
            all_packages.add(spec)
            deps = self._get_dependencies(name)
            all_packages.update(deps)

        logger.info(f"Installing {len(all_packages)} packages (including dependencies)")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.install_package, spec): spec for spec in all_packages}
            successful = []
            failed = []

            for future in concurrent.futures.as_completed(futures):
                spec = futures[future]
                try:
                    if future.result():
                        successful.append(spec)
                    else:
                        failed.append(spec)
                except Exception as e:
                    failed.append(f"{spec}: {str(e)}")

            if successful:
                logger.info("\nSuccessfully installed packages:")
                for spec in sorted(successful):
                    name = self._get_base_name(spec)
                    version = self._get_installed_version(name)
                    if version:
                        logger.info(f"  ✓ {name}=={version}")

            if failed:
                raise Exception("Some packages failed to install:\n" + "\n".join(failed))

    def uninstall_package(self, package_name):
        base_name = self._get_base_name(package_name)
        try:
            cmd = ["pip", "uninstall", "-y", base_name]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, stderr = process.communicate()

            if process.returncode != 0:
                if "externally-managed-environment" in stderr:
                    cmd.append("--break-system-packages")
                    subprocess.check_call(cmd)
                else:
                    raise Exception(stderr)

            data = self._load_packages()
            if base_name in data["packages"]:
                del data["packages"][base_name]
                self._save_packages(data)

            logger.info(f"✓ {base_name} uninstalled successfully")

        except Exception as e:
            raise Exception(f"Failed to uninstall {base_name}: {str(e)}")

    def update_package(self, package_name):
        base_name = self._get_base_name(package_name)
        try:
            current_version = self._get_installed_version(base_name)
            cmd = ["pip", "install", "--upgrade", "--user", "--cache-dir", self.cache_dir, base_name]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            with tqdm(total=100, desc=f"Updating {base_name}", position=0, leave=True) as pbar:
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        if "Collecting" in output:
                            pbar.update(20)
                        elif "Downloading" in output:
                            pbar.update(30)
                        elif "Installing" in output:
                            pbar.update(40)
                        elif "Successfully" in output:
                            pbar.update(10)

            if process.returncode != 0:
                stderr = process.stderr.read()
                if "externally-managed-environment" in stderr:
                    cmd.append("--break-system-packages")
                    subprocess.check_call(cmd)
                else:
                    raise Exception(f"Update failed: {stderr}")

            new_version = self._get_installed_version(base_name)
            if not new_version:
                raise Exception(f"Could not determine version for {base_name}")

            if current_version == new_version:
                logger.info(f"✓ {base_name} is already at the latest version {new_version}")
            else:
                logger.info(f"✓ {base_name} updated from {current_version} to {new_version}")

            data = self._load_packages()
            data["packages"][base_name] = {
                "version": new_version,
                "update_date": datetime.now().isoformat(),
                "security_hash": self._check_package_security(base_name)
            }

            self._save_packages(data)

        except Exception as e:
            raise Exception(f"Failed to update {base_name}: {str(e)}")

    def _normalize_package_data(self):
        """Normalize package data by consolidating version constraints"""
        data = self._load_packages()
        normalized = {"packages": {}}

        for name, info in data["packages"].items():
            base_name = self._get_base_name(name)
            if base_name not in normalized["packages"]:
                normalized["packages"][base_name] = {
                    "version": info["version"],
                    "install_date": info["install_date"],
                    "security_hash": info.get("security_hash"),
                    "constraints": []
                }
            if "==" not in name and any(c in name for c in "<>!=~"):
                normalized["packages"][base_name]["constraints"].append(name.split(base_name)[1].strip())

        return normalized

    def list_packages(self):
        data = self._normalize_package_data()
        if not data.get("packages"):
            logger.info("No packages installed")
            return

        # Header with clean border
        logger.info("\n📦 Package Version Dashboard")
        logger.info("═" * 50)

        # Package listing with tree structure
        for name, info in sorted(data["packages"].items()):
            try:
                current_version = self._get_installed_version(name)
                if current_version:
                    latest_version = self._get_latest_version(name)
                    security_hash = self._check_package_security(name)
                    metadata = self._get_package_metadata(name)

                    # Status indicators
                    version_status = "✓" if (latest_version and version.parse(current_version) >= version.parse(latest_version)) else "⚠"
                    security_status = "🔒" if security_hash else "  "

                    # Package header with version, security, and metadata
                    logger.info(f"\n{version_status} {security_status} {name}")
                    logger.info("├── Current: " + current_version)
                    if latest_version and version.parse(current_version) < version.parse(latest_version):
                        logger.info("├── Latest:  " + latest_version)

                    # Show version constraints if any
                    constraints = info.get("constraints", [])
                    if constraints:
                        logger.info("├── Constraints: " + ", ".join(constraints))

                    # Show metadata if available
                    if metadata:
                        logger.info("├── License: " + metadata["license"])
                        logger.info("├── Author:  " + metadata["author"])
                        if len(metadata["summary"]) > 80:
                            logger.info("├── Summary: " + metadata["summary"][:77] + "...")
                        else:
                            logger.info("├── Summary: " + metadata["summary"])

                    # Show dates
                    logger.info("├── Install Date: " + info.get("install_date", "Unknown").split("T")[0])
                    if info.get("update_date"):
                        logger.info("├── Last Update: " + info["update_date"].split("T")[0])

                    # Get and display dependencies
                    deps = self._get_dependencies(name) or []
                    if deps:
                        logger.info("└── Dependencies:")
                        # Sort dependencies by their importance (direct dependencies first)
                        direct_deps = []
                        transitive_deps = []
                        for dep in deps:
                            try:
                                dep_version = self._get_installed_version(dep)
                                dep_str = f"{dep} ({dep_version})" if dep_version else f"{dep} (not installed)"
                                if dep in data["packages"]:
                                    direct_deps.append(dep_str)
                                else:
                                    transitive_deps.append(dep_str)
                            except Exception:
                                transitive_deps.append(f"{dep} (version unknown)")

                        # Display direct dependencies
                        if direct_deps:
                            logger.info("    ├── Direct:")
                            for i, dep in enumerate(sorted(direct_deps)):
                                is_last = i == len(direct_deps) - 1 and not transitive_deps
                                prefix = "    │   └── " if is_last else "    │   ├── "
                                logger.info(prefix + dep)

                        # Display transitive dependencies
                        if transitive_deps:
                            if direct_deps:
                                logger.info("    └── Transitive:")
                            for i, dep in enumerate(sorted(transitive_deps)):
                                is_last = i == len(transitive_deps) - 1
                                prefix = "        └── " if is_last else "        ├── "
                                logger.info(prefix + dep)
                    else:
                        logger.info("└── No dependencies")
                else:
                    logger.info(f"? {name} (not found)")
            except Exception as e:
                logger.error(f"! {name} (error: {str(e)})")

        # Legend with box drawing characters
        logger.info("\n" + "─" * 20)
        logger.info("Legend:")
        logger.info("✓ - Up to date")
        logger.info("⚠ - Update available")
        logger.info("🔒 - Security hash verified")
        logger.info("? - Not installed")
        logger.info("! - Error checking")