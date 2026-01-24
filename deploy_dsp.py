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
        # Use a relative path placeholder to allow Lean to use its own defaults
        "LEAN_LIBRARY_PATH": "/usr/lib/x86_64-linux-gnu:"
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
    mathlib_path = repo_path / "mathlib4"
    build_marker = mathlib_path / "build" / ".build_complete"
    
    # Check for actual binaries, not just a marker
    olean_sample = mathlib_path / ".lake" / "build" / "lib" / "Mathlib" / "Data" / "Nat" / "Basic.olean"
    
    if build_marker.exists() and olean_sample.exists():
        print("✅ Mathlib4 is fully built and binaries are present.")
        return

    print("🔨 Building Mathlib4 in stages to ensure persistence...")
    
    # Stage 1: Core dependencies
    # This gets the 'Unit' and 'Nat' basics out of the way
    # run_command("source /root/.elan/env && lake build Init", 
    #             cwd=mathlib_path, shell=True, description="Building Init")
    # workspace_volume.commit() # Save progress immediately

    # Stage 2: Attempt Cache
    run_command("source /root/.elan/env && lake exe cache get || echo 'Cache miss'", 
                cwd=mathlib_path, shell=True, description="Fetching Cache")

    # Stage 3: The Full Build
    # This is the long one. If it hangs, the 'Init' we just saved stays safe.
    print("🚀 Starting full Mathlib build (this may take 20-40 mins)...")
    run_command("source /root/.elan/env && lake build", 
                cwd=mathlib_path, shell=True, description="Full Build")
    
    run_command("mkdir -p build && touch build/.build_complete", cwd=mathlib_path, shell=True)
    workspace_volume.commit() 
    print("✅ Build committed to Volume.")


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

def test_lean_mathlib(repo_path: Path):
    print("🧪 Testing Mathlib integration...")
    mathlib_path = repo_path / "mathlib4"
    
    # We pipe the JSON into the REPL while ensuring the environment is sourced
    test_input = '{"cmd": "import Mathlib.Data.Nat.Basic\\n#check Nat.add_comm"}'
    
    # WRAP the command in a bash shell that sources the environment
    full_cmd = f"source /root/.elan/env && echo '{test_input}' | lake env lake exe repl"
    
    try:
        result = subprocess.run(
            full_cmd,
            cwd=mathlib_path,
            capture_output=True,
            text=True,
            shell=True,
            executable="/bin/bash"
        )
        
        if "Nat.add_comm" in result.stdout:
            print("✅ Mathlib check successful!")
        else:
            print(f"⚠️ REPL Response: {result.stdout}")
    except Exception as e:
        print(f"❌ Mathlib Test Failed: {e}")

def test_lean_repl(repo_path: Path):
    print("🧪 Testing Lean REPL interactive session...")
    mathlib_path = repo_path / "mathlib4"
    
    # Simple Lean command to check if it can evaluate 1 + 1
    test_input = '{"cmd": "import Lean\\n#eval 1 + 1"}'
    
    try:
        # We run the repl binary and pipe the test_input into it
        result = subprocess.run(
            ["lake", "env", "lake", "exe", "repl"], # Wrap the command in 'lake env'
            input=test_input,
            cwd=mathlib_path,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ REPL Response:", result.stdout)
        if "2" in result.stdout:
            print("✨ Lean Server is fully operational!")
    except Exception as e:
        print(f"❌ REPL Test Failed: {e}")
        # Check if it's a library linking error (common with OpenBLAS)
        if "libopenblas" in str(e):
            print("💡 Hint: OpenBLAS linking is still broken.")
        raise

def test_lean_server():
    from dsp.utils import load_dataset, load_config
    print("🧪 Testing Lean server startup...")
    config = "config/default.py"
    cfg = load_config(config)
    try:
        from dsp import Draft, Sketch, Prove
        Sketch.launch_lean4server(max_lean4_requests = cfg.sketch_leanserver_num, **cfg.sketch_verify_config)
        Prove.launch_lean4server(max_lean4_requests = cfg.prove_leanserver_num, **cfg.prove_verify_config)
        print("✅ Lean server started successfully!")
    except Exception as e:
        print(f"❌ Lean server failed to start: {e}")
        raise

def debug_lean_paths(repo_path: Path):
    print("\n🕵️ --- LEAN PATH DIAGNOSTIC START ---")
    mathlib_path = repo_path / "mathlib4"
    
    # 1. Check Physical Location of Binaries
    sample_path = mathlib_path / ".lake" / "build" / "lib" / "Init.olean"
    print(f"📂 Physical check: Does Init.olean exist? {'✅ YES' if sample_path.exists() else '❌ NO'}")
    print(f"📍 Full Physical Path: {sample_path.absolute()}")

    # 2. Check Lean's Internal Search Paths
    print("\n🔍 Lean's Search Environment:")
    # --print-libdir shows where the core toolchain is
    run_command("source /root/.elan/env && lean --print-libdir", 
                cwd=mathlib_path, shell=True, description="Toolchain Lib Dir")
    
    # lake env lean --print-libdir shows where the current project looks
    run_command("source /root/.elan/env && lake env lean --print-libdir", 
                cwd=mathlib_path, shell=True, description="Project Active Lib Dir")

    # 3. Check for LEAN_PATH environment variable
    print("\n🌐 Environment Variables:")
    run_command("env | grep LEAN || echo 'No LEAN variables set'", shell=True)
    
    # 4. List the first few files in the build directory to confirm structure
    print("\n📁 Build Directory Sample:")
    run_command(f"ls -R {mathlib_path}/.lake/build/lib | head -n 10", shell=True)
    
    print("🕵️ --- LEAN PATH DIAGNOSTIC END ---\n")

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

    # Initial commit of workspace
    print("💾 Saving build to Volume...")
    workspace_volume.commit()
    
    # Step 4: Run the workflow with unbuffered output
    print("🏃 Starting the DSP workflow...")

    # print current path
    print(f"Current working directory: {os.getcwd()}")

    # Test lean server setup
    os.chdir(repo_path)
    # NEW: Run the debugger here
    debug_lean_paths(repo_path)

    test_lean_repl(repo_path)
    test_lean_mathlib(repo_path)
    # test_lean_server()
    
    # Use unbuffered Python output and verbose logging
    # workflow_cmd = """
    # source /root/.elan/env
    # export PYTHONUNBUFFERED=1
    # python -u dsp_workflow.py --config config/default.py 2>&1 | tee -a workflow.log
    # """

    # workflow_cmd = """
    # source /root/.elan/env
    # export PYTHONUNBUFFERED=1
    # python quick_start.py 2>&1 | tee -a workflow.log
    # """
    
    # run_command(
    #     workflow_cmd,
    #     cwd=repo_path,
    #     shell=True,
    #     description="Running DSP workflow"
    # )
    
    # # Step 5: Commit changes to volume
    # print("💾 Committing workspace to volume...")
    # workspace_volume.commit()
    
    # print("✅ Workflow completed successfully!")


# ============================================================================
# ENTRY POINT
# ============================================================================

@app.local_entrypoint()
def main():
    """Entry point for running the function."""
    run_remote_prover.remote()