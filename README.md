# Clone the repository
git clone https://github.com/yourusername/PackageEngine.git

# Navigate to the project directory
cd PackageEngine

# Install the package
pip install -e .
```

## Usage

### Basic Commands

```bash
# Install packages
python pypackman.py pkgx install package_name

# Install multiple packages
python pypackman.py pkgx install package1 package2

# Remove a package
python pypackman.py pkgx remove package_name

# Update a package
python pypackman.py pkgx update package_name

# List installed packages
python pypackman.py pkgx list

# Create a virtual environment
python pypackman.py pkgx venv myenv
```

### Package Version Dashboard

The `list` command provides a rich visualization of installed packages:

```bash
python pypackman.py pkgx list
```

Example output:
```
📦 Package Version Dashboard
══════════════════════════════════════════════════

✓ 🔒 requests
├── Current: 2.32.3
├── License: Apache-2.0
├── Author:  Kenneth Reitz
├── Summary: Python HTTP for Humans.
├── Install Date: 2025-02-16
└── Dependencies:
    ├── Direct:
    │   ├── certifi (2025.1.31)
    │   ├── charset-normalizer (3.4.1)
    │   ├── idna (3.10)
    │   └── urllib3 (2.3.0)
```

The dashboard shows:
- Current and latest versions
- Security status
- Installation dates
- Version constraints
- Direct and transitive dependencies
- Package metadata:
  - License information
  - Author details
  - Package description

### Status Indicators

- ✓ Package is up to date
- ⚠ Update available
- 🔒 Security hash verified
- ? Package not found
- ! Error checking package

### Tree Structure

Dependencies are organized in a hierarchical tree:
```
package_name
├── Current: 1.0.0
├── Latest: 1.1.0
├── License: MIT
├── Author: John Doe
├── Summary: Package description
└── Dependencies:
    ├── Direct:
    │   ├── dep1 (1.0.0)
    │   └── dep2 (2.0.0)
    └── Transitive:
        └── dep3 (1.5.0)