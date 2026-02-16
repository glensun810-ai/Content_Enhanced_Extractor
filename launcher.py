#!/usr/bin/env python3
"""
Launcher for the Multimodal Website Content Extractor
Provides options to run the GUI or command-line interface
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

def run_gui():
    """Launch the GUI interface"""
    try:
        subprocess.Popen([sys.executable, "gui_interface.py"])
    except Exception as e:
        print(f"Error launching GUI: {e}")
        messagebox.showerror("Error", f"Could not launch GUI: {e}")

def run_cli():
    """Launch the command-line interface"""
    try:
        subprocess.call([sys.executable, "main.py"])
    except Exception as e:
        print(f"Error launching CLI: {e}")
        messagebox.showerror("Error", f"Could not launch CLI: {e}")

def main():
    root = tk.Tk()
    root.title("Multimodal Website Content Extractor - Launcher")
    root.geometry("400x200")
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Main frame
    main_frame = tk.Frame(root)
    main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
    
    # Title
    title_label = tk.Label(main_frame, text="Multimodal Website Content Extractor", font=("Arial", 16, "bold"))
    title_label.pack(pady=10)
    
    # Description
    desc_label = tk.Label(main_frame, text="Choose your preferred interface:", font=("Arial", 12))
    desc_label.pack(pady=10)
    
    # Buttons frame
    buttons_frame = tk.Frame(main_frame)
    buttons_frame.pack(pady=20)
    
    # GUI Button
    gui_button = tk.Button(buttons_frame, text="Launch GUI Interface", 
                          command=run_gui, font=("Arial", 12), 
                          bg="#4CAF50", fg="white", 
                          padx=20, pady=10, width=20)
    gui_button.pack(side=tk.TOP, pady=10)
    
    # CLI Button
    cli_button = tk.Button(buttons_frame, text="Launch Command-Line Interface", 
                          command=run_cli, font=("Arial", 12), 
                          bg="#2196F3", fg="white", 
                          padx=20, pady=10, width=20)
    cli_button.pack(side=tk.TOP, pady=10)
    
    # Exit button
    exit_button = tk.Button(main_frame, text="Exit", 
                           command=root.destroy, font=("Arial", 12),
                           bg="#f44336", fg="white",
                           padx=20, pady=5)
    exit_button.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()