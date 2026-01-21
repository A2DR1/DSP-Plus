import modal
import subprocess
from pathlib import Path

# ============================================================================
# IMAGE CONFIGURATION
# ============================================================================

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git", 
        "cmake", 
        "curl", 
        "build-essential", 
        "libgmp-dev", 
        "libopenblas-dev",  # Critical for LeanCopilot
        "pkg-config"
    )
    .run_commands(
        # Install Lean toolchain
        "curl https://elan.lean-lang.org/elan-init.sh -sSf | sh -s -- -y",
        # Pin specific toolchain version
        "/root/.elan/bin/elan toolchain install v4.17.0-rc1",
        "/root/.elan/bin/elan default v4.17.0-rc1"
    )
    .env({
        "PATH": "/root/.elan/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        # Ensure Lean finds system OpenBLAS
        "LEAN_LIBRARY_PATH": "/usr/lib/x86_64-linux-gnu"
    })
    .pip_install(
        "pexpect==4.9.0",
        "easydict==1.13",
        "numpy==2.2.5",
        "openai==1.78.1",
        "uvicorn==0.34.2",
        "fastapi==0.115.12",
        "loguru==0.7.3"
    )
)

# ============================================================================
# MODAL APP CONFIGURATION
# ============================================================================

app = modal.App("dsp-plus-main")
workspace_volume = modal.Volume.from_name("lean-workspace", create_if_missing=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_command(cmd, cwd=None, shell=False, check=True, description=None):
    """Run a command with better logging and error handling."""
    if description:
        print(f"🔧 {description}")
    
    try:
        if shell:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                check=check,
                capture_output=False,
                text=True,
                executable="/bin/bash"
            )
        else:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                capture_output=False,
                text=True
            )
        
        if result.stdout:
            print(result.stdout)
        return result
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        raise


def setup_repository(workspace_path: Path, repo_url: str, branch: str):
    """Clone or update the repository."""
    repo_path = workspace_path / "DSP-Plus"
    
    if not repo_path.exists():
        print("🚀 Cloning DSP-Plus repository...")
        run_command(
            ["git", "clone", "--recurse-submodules", repo_url],
            cwd=workspace_path,
            description="Cloning repository"
        )
    else:
        print("🔄 Repository exists. Updating from GitHub...")
        # Reset any local changes
        run_command(
            ["git", "reset", "--hard"],
            cwd=repo_path,
            description="Resetting local changes"
        )
        # Fetch latest changes
        run_command(
            ["git", "fetch", "origin"],
            cwd=repo_path,
            description="Fetching updates"
        )
    
    # Ensure correct branch
    print(f"🌿 Ensuring {branch} branch is active...")
    run_command(
        ["git", "checkout", branch],
        cwd=repo_path,
        description=f"Checking out {branch}"
    )
    
    # Pull latest changes
    run_command(
        ["git", "pull", "origin", branch],
        cwd=repo_path,
        description="Pulling latest changes"
    )
    
    # Update submodules
    run_command(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=repo_path,
        description="Updating submodules"
    )
    
    return repo_path


def setup_openblas_for_leancopilot(repo_path: Path):
    """Setup system OpenBLAS for LeanCopilot to avoid building from source."""
    print("🔗 Setting up system OpenBLAS for LeanCopilot...")
    
    mathlib_path = repo_path / "mathlib4"
    leancopilot_lib = mathlib_path / ".lake" / "packages" / "LeanCopilot" / ".lake" / "build" / "lib"
    leancopilot_lib.mkdir(parents=True, exist_ok=True)
    
    # System OpenBLAS location
    system_openblas = Path("/usr/lib/x86_64-linux-gnu/libopenblas.so.0")
    target_link = leancopilot_lib / "libopenblas.so"
    
    # Create symlink to system library
    if target_link.exists() or target_link.is_symlink():
        target_link.unlink()
    
    target_link.symlink_to(system_openblas)
    print(f"✅ Linked {target_link} -> {system_openblas}")


def build_mathlib(repo_path: Path):
    """Build Mathlib4 and LeanCopilot if not already built."""
    mathlib_path = repo_path / "mathlib4"
    build_marker = mathlib_path / "build" / ".build_complete"
    
    # Check if we need to build
    if build_marker.exists():
        print("✅ Mathlib4 already built (found .build_complete marker)")
        return
    
    print("🔨 Building Mathlib4 and LeanCopilot...")
    
    # Build script with proper environment sourcing
    build_script = """
    set -e  # Exit on error
    source /root/.elan/env
    
    # Ensure OpenBLAS is found
    export LEAN_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LEAN_LIBRARY_PATH}
    
    # Build in order
    echo "Building RulesetInit..."
    lake build RulesetInit
    
    echo "Building LeanCopilot..."
    lake build LeanCopilot
    
    echo "Building repl..."
    lake build repl
    
    echo "Building all remaining dependencies..."
    lake build
    
    # Create completion marker
    mkdir -p build
    touch build/.build_complete
    echo "✅ Build completed successfully"
    """
    
    run_command(
        build_script,
        cwd=mathlib_path,
        shell=True,
        description="Building Mathlib4 components"
    )


def verify_dependencies():
    """Verify critical dependencies are available."""
    print("🔍 Verifying dependencies...")
    
    checks = [
        (["lean", "--version"], "Lean"),
        (["lake", "--version"], "Lake"),
        (["python", "--version"], "Python"),
    ]
    
    for cmd, name in checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"✅ {name}: {result.stdout.strip()}")
        except Exception as e:
            print(f"❌ {name} not found: {e}")
            raise

# ============================================================================
# MAIN FUNCTION
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("dsp-plus-secrets")],
    volumes={"/root/workspace": workspace_volume},
    # Increase Memory to 64GB and CPU to 16 to handle the I/O storm
    memory=65536,      
    cpu=16.0,          
    timeout=21600,     
    retries=0          
)
def run_remote_prover():
    """Main function to run the DSP-Plus prover."""
    import os
    
    workspace_path = Path("/root/workspace")
    os.chdir(workspace_path)
    
    # Step 1: Verify dependencies
    verify_dependencies()
    
    # Step 2: Setup repository
    repo_path = setup_repository(
        workspace_path=workspace_path,
        repo_url="https://github.com/A2DR1/DSP-Plus.git",
        branch="Austin_01"
    )
    
    # Step 3: Setup OpenBLAS and build Mathlib4 if needed
    os.chdir(repo_path)
    setup_openblas_for_leancopilot(repo_path)
    build_mathlib(repo_path)
    
    # Step 4: Run the workflow with unbuffered output
    print("🏃 Starting the DSP workflow...")

    # print current path
    print(f"Current working directory: {os.getcwd()}")
    
    # Use unbuffered Python output and verbose logging
    # workflow_cmd = """
    # source /root/.elan/env
    # export PYTHONUNBUFFERED=1
    # python -u dsp_workflow.py --config config/default.py 2>&1 | tee -a workflow.log
    # """

    workflow_cmd = """
    source /root/.elan/env
    export PYTHONUNBUFFERED=1
    python quick_start.py 2>&1 | tee -a workflow.log
    """
    
    run_command(
        workflow_cmd,
        cwd=repo_path,
        shell=True,
        description="Running DSP workflow"
    )
    
    # Step 5: Commit changes to volume
    print("💾 Committing workspace to volume...")
    workspace_volume.commit()
    
    print("✅ Workflow completed successfully!")


# ============================================================================
# ENTRY POINT
# ============================================================================

@app.local_entrypoint()
def main():
    """Entry point for running the function."""
    run_remote_prover.remote()