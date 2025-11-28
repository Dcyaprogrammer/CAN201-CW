# Ryu 4.34 Installation Fix for Python 3.12

## 📋 Root Cause Analysis

### Why Can't We Install Directly?

1. **Python 3.12 Removed `distutils` Module**
   - Marked as deprecated starting from Python 3.10
   - Officially removed from standard library in Python 3.12 (October 2023)
   - `ryu` 4.34's build process depends on `distutils`

2. **setuptools API Changes**
   - `ryu` 4.34's `hooks.py` tries to access `easy_install.get_script_args`
   - This attribute doesn't exist in newer setuptools versions
   - Results in `AttributeError: 'types.SimpleNamespace' object has no attribute 'get_script_args'`

3. **No Pre-built Wheel Packages**
   - No pre-compiled wheels available on PyPI for Python 3.12
   - Must build from source, but source code has compatibility issues

## 🔧 Fix Solution

Manually fix the compatibility issues in the source code, then install from local directory.

### Step 1: Download Ryu Source Code

```bash
# Create temporary directory
mkdir -p /tmp/ryu-fix
cd /tmp/ryu-fix

# Download ryu 4.34 source code
curl -L https://github.com/faucetsdn/ryu/archive/refs/tags/v4.34.tar.gz -o ryu-4.34.tar.gz

# Extract
tar -xzf ryu-4.34.tar.gz
```

### Step 2: Fix hooks.py File

Navigate to the extracted directory, backup and modify `ryu/hooks.py`:

```bash
cd ryu-4.34

# Backup original file
cp ryu/hooks.py ryu/hooks.py.bak
```

Find the `save_orig()` function (around line 32-36), change:

```python
def save_orig():
    """Save original easy_install.get_script_args.
    This is necessary because pbr's setup_hook is sometimes called
    before ours."""
    _main_module()._orig_get_script_args = easy_install.get_script_args
```

**To:**

```python
def save_orig():
    """Save original easy_install.get_script_args.
    This is necessary because pbr's setup_hook is sometimes called
    before ours."""
    # Patch: Handle case where get_script_args doesn't exist in newer setuptools
    if hasattr(easy_install, 'get_script_args'):
        _main_module()._orig_get_script_args = easy_install.get_script_args
    else:
        # Create a dummy function if it doesn't exist
        def dummy_get_script_args(*args, **kwargs):
            return []
        _main_module()._orig_get_script_args = dummy_get_script_args
```

Also, in the `setup_hook()` function (around line 60), find:

```python
    packaging.override_get_script_args = my_get_script_args
    easy_install.get_script_args = my_get_script_args
```

**Change to:**

```python
    packaging.override_get_script_args = my_get_script_args
    if hasattr(easy_install, 'get_script_args'):
        easy_install.get_script_args = my_get_script_args
```

### Step 3: Install Fixed Source Code

**Option A: Using uv (Recommended)**

```bash
# Return to project directory
cd /Users/dopamine/CAN201-CW  # Replace with your project path

# Install from local directory using uv
uv pip install /tmp/ryu-fix/ryu-4.34
```

**Option B: Using Standard pip**

```bash
# Return to project directory
cd /Users/dopamine/CAN201-CW  # Replace with your project path

# Activate your virtual environment first (if using one)
# source venv/bin/activate  # On Linux/Mac
# venv\Scripts\activate      # On Windows

# Install from local directory using pip
pip install /tmp/ryu-fix/ryu-4.34
```

### Step 4: Verify Installation

**If using uv:**

```bash
# Check if ryu is installed successfully
uv pip list | grep ryu

# Test import
uv run python -c "import ryu; from ryu import version; print(f'Ryu {version} installed successfully!')"
```

**If using standard pip:**

```bash
# Check if ryu is installed successfully
pip list | grep ryu

# Test import
python -c "import ryu; from ryu import version; print(f'Ryu {version} installed successfully!')"
```

### Step 5: Clean Up Temporary Files (Optional)

```bash
rm -rf /tmp/ryu-fix
```

## 🚀 One-Click Fix Script

If you want an automated script, you can use the following commands:

**For uv users:**

```bash
# Create temporary directory and download
mkdir -p /tmp/ryu-fix && cd /tmp/ryu-fix
curl -L https://github.com/faucetsdn/ryu/archive/refs/tags/v4.34.tar.gz -o ryu-4.34.tar.gz
tar -xzf ryu-4.34.tar.gz

# Use sed to automatically fix hooks.py
cd ryu-4.34

# Fix save_orig function
sed -i.bak 's/_main_module()._orig_get_script_args = easy_install.get_script_args/if hasattr(easy_install, "get_script_args"):\
        _main_module()._orig_get_script_args = easy_install.get_script_args\
    else:\
        def dummy_get_script_args(*args, **kwargs):\
            return []\
        _main_module()._orig_get_script_args = dummy_get_script_args/' ryu/hooks.py

# Fix easy_install.get_script_args assignment in setup_hook function
sed -i.bak2 's/easy_install.get_script_args = my_get_script_args/if hasattr(easy_install, "get_script_args"):\
        easy_install.get_script_args = my_get_script_args/' ryu/hooks.py

# Install using uv
cd /Users/dopamine/CAN201-CW  # Replace with your project path
uv pip install /tmp/ryu-fix/ryu-4.34
```

**For standard pip users:**

```bash
# Create temporary directory and download
mkdir -p /tmp/ryu-fix && cd /tmp/ryu-fix
curl -L https://github.com/faucetsdn/ryu/archive/refs/tags/v4.34.tar.gz -o ryu-4.34.tar.gz
tar -xzf ryu-4.34.tar.gz

# Use sed to automatically fix hooks.py
cd ryu-4.34

# Fix save_orig function
sed -i.bak 's/_main_module()._orig_get_script_args = easy_install.get_script_args/if hasattr(easy_install, "get_script_args"):\
        _main_module()._orig_get_script_args = easy_install.get_script_args\
    else:\
        def dummy_get_script_args(*args, **kwargs):\
            return []\
        _main_module()._orig_get_script_args = dummy_get_script_args/' ryu/hooks.py

# Fix easy_install.get_script_args assignment in setup_hook function
sed -i.bak2 's/easy_install.get_script_args = my_get_script_args/if hasattr(easy_install, "get_script_args"):\
        easy_install.get_script_args = my_get_script_args/' ryu/hooks.py

# Install using pip (activate virtual environment first if needed)
cd /Users/dopamine/CAN201-CW  # Replace with your project path
pip install /tmp/ryu-fix/ryu-4.34
```

## 📝 Fix Explanation

### Why This Fix Works?

1. **Backward Compatibility**
   - Uses `hasattr()` to check if attribute exists
   - If exists (old setuptools), uses original logic
   - If doesn't exist (new setuptools), uses fallback function

2. **Functional Impact**
   - `get_script_args` is mainly used for generating installation scripts
   - Newer setuptools may handle script generation differently
   - Fallback function returns empty list, prevents errors, doesn't affect core functionality

3. **Safety**
   - The fix is defensive and won't break existing functionality
   - Still works in old environments

## ⚠️ Important Notes

1. **Re-installation Requires Re-fixing**
   - If you delete and recreate virtual environment, you need to redo the fix steps
   - Consider saving the fixed source package or using automation scripts

2. **Team Collaboration**
   - If using `pyproject.toml` for dependency management, other team members will face the same issue
   - Consider adding fix scripts to project documentation or CI/CD pipeline

3. **Long-term Solution**
   - Submit issue/PR to ryu project to push for official fix
   - Watch for newer ryu versions that support Python 3.12

## 🔍 Troubleshooting

If installation still fails:

1. **Check Python Version**
   ```bash
   python3 --version  # Should be 3.12 or higher
   ```

2. **Check setuptools Version**
   ```bash
   # If using uv
   uv pip list | grep setuptools
   
   # If using standard pip
   pip list | grep setuptools
   ```

3. **Ensure Correct File Was Fixed**
   ```bash
   cat /tmp/ryu-fix/ryu-4.34/ryu/hooks.py | grep -A 5 "def save_orig"
   ```

4. **Clear Cache and Retry**
   ```bash
   # If using uv
   uv cache clean
   uv pip install /tmp/ryu-fix/ryu-4.34
   
   # If using standard pip
   pip cache purge
   pip install /tmp/ryu-fix/ryu-4.34
   ```

## 📚 References

- [PEP 632 - Deprecate distutils](https://peps.python.org/pep-0632/)
- [Ryu GitHub Repository](https://github.com/faucetsdn/ryu)
- [Python 3.12 Release Notes](https://docs.python.org/3.12/whatsnew/3.12.html)

---

**Last Updated**: November 2024
**Compatible Environment**: Python 3.12+, uv or standard pip package manager

## 💡 Important Note About Package Managers

**The issue is NOT caused by uv or pip** - it's a compatibility problem between Python 3.12 and ryu 4.34. Whether you use `uv pip install` or standard `pip install`, you will encounter the same error. The fix steps are identical for both package managers - only the installation command differs:

- **uv**: `uv pip install /tmp/ryu-fix/ryu-4.34`
- **standard pip**: `pip install /tmp/ryu-fix/ryu-4.34`

The source code fix (Step 2) is the same regardless of which package manager you use.
