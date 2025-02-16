import argparse
import sys
from .package_handler import PackageEngine
from .venv_manager import VenvManager
from .utils import setup_logger

logger = setup_logger()

def create_parser():
    parser = argparse.ArgumentParser(
        description="PackageEngine - Advanced Python Package Manager"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    install_parser = subparsers.add_parser("pkgx", help="PackageEngine commands")
    install_subparsers = install_parser.add_subparsers(dest="subcommand")

    install_cmd = install_subparsers.add_parser("install", help="Install packages")
    install_cmd.add_argument("packages", nargs="+", help="Package names with optional versions")

    install_subparsers.add_parser("list", help="List installed packages")

    uninstall_cmd = install_subparsers.add_parser("remove", help="Remove packages")
    uninstall_cmd.add_argument("package", help="Package name")

    update_cmd = install_subparsers.add_parser("update", help="Update packages")
    update_cmd.add_argument("package", help="Package name")

    venv_cmd = install_subparsers.add_parser("venv", help="Virtual environment commands")
    venv_cmd.add_argument("name", help="Name of the virtual environment")

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command or (args.command == "pkgx" and not args.subcommand):
        parser.print_help()
        sys.exit(1)

    try:
        engine = PackageEngine()
        venv_manager = VenvManager()

        if args.command == "pkgx":
            if args.subcommand == "install":
                engine.install_multiple(args.packages)
            elif args.subcommand == "remove":
                engine.uninstall_package(args.package)
            elif args.subcommand == "update":
                engine.update_package(args.package)
            elif args.subcommand == "list":
                engine.list_packages()
            elif args.subcommand == "venv":
                venv_manager.create_venv(args.name)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)