# install_openvoice.py - Run this to install OpenVoice
import subprocess
import sys
import os

def run_command(command):
    """Run a command and print output"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Error output: {e.stderr}")
        return False

def install_openvoice():
    print("Installing OpenVoice...")
    
    # Step 1: Clone the OpenVoice repository
    if not os.path.exists("OpenVoice"):
        print("Cloning OpenVoice repository...")
        if not run_command("git clone https://github.com/myshell-ai/OpenVoice.git"):
            print("Failed to clone repository. Make sure git is installed.")
            return False
    
    # Step 2: Install OpenVoice
    print("Installing OpenVoice package...")
    if not run_command("pip install -e ./OpenVoice"):
        print("Failed to install OpenVoice")
        return False
    
    print("OpenVoice installation completed!")
    return True

if __name__ == "__main__":
    install_openvoice()