import modal
import os

# 1. Image with ALL dependencies, including OpenBLAS for LeanCopilot
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git", 
        "cmake", 
        "curl", 
        "build-essential", 
        "libgmp-dev", 
        "libopenblas-dev", 
        "pkg-config"
    )
    .run_commands(
        "curl https://elan.lean-lang.org/elan-init.sh -sSf | sh -s -- -y",
        # Pinning the specific toolchain to avoid runtime downloads
        "/root/.elan/bin/elan toolchain install v4.17.0-rc1",
        "/root/.elan/bin/elan default v4.17.0-rc1"
    )
    .env({"PATH": "/root/.elan/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})
    # Correctly formatted Python dependencies with specific versions
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

app = modal.App("dsp-plus-main")
workspace_volume = modal.Volume.from_name("lean-workspace", create_if_missing=True)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("dsp-plus-secrets")],
    volumes={"/root/workspace": workspace_volume},
    memory=32768,      # Critical for Mathlib builds
    timeout=14400      # 4 hours for the heavy first run
)
def run_remote_prover():
    import subprocess
    import os
    os.chdir("/root/workspace")
    
    # --- Step 2: Robust Clone or Update ---
    if not os.path.exists("DSP-Plus"):
        print("🚀 Repository missing. Cloning DSP-Plus...")
        subprocess.run([
            "git", "clone", "--recurse-submodules", 
            "https://github.com/A2DR1/DSP-Plus.git"
        ], check=True)
        os.chdir("DSP-Plus")
    else:
        print("🔄 Repository exists. Updating from GitHub...")
        os.chdir("DSP-Plus")
        # Reset local changes in the cloud to avoid merge conflicts
        subprocess.run(["git", "reset", "--hard"], check=True)
        # Pull the latest changes for the Austin_01 branch
        subprocess.run(["git", "pull", "origin", "Austin_01"], check=True)
    
    # Ensure you are on the correct branch
    print("🌿 Ensuring Austin_01 branch is active...")
    subprocess.run(["git", "checkout", "Austin_01"], check=True)
    
    # Update submodules in case mathlib4 or others changed
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
    
    # --- Step 4: Build Mathlib4 ---
    if not os.path.exists("mathlib4/build"):
        print("🔨 Step 4: Deep build of Mathlib4/LeanCopilot...")
        os.chdir("mathlib4")
        # Sourcing the environment is safer for nested lake builds
        build_script = """
        source /root/.elan/env
        lake build RulesetInit
        lake build LeanCopilot
        lake build repl
        lake build
        """
        subprocess.run(build_script, shell=True, executable="/bin/bash", check=True)
        os.chdir("..")

    # --- Start Execution ---
    print("🏃 Starting the 244-problem dataset run...")
    subprocess.run("source /root/.elan/env && python dsp_workflow.py --config configs/default.py", shell=True, executable="/bin/bash", check=True)
    
    workspace_volume.commit() #