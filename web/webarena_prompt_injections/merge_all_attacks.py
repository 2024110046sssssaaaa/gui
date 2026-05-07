#!/usr/bin/env python3
"""
Script to merge all attack configurations from different projects
into a single unified attack configuration file.
"""

import json
import os
from pathlib import Path

def load_json_file(filepath):
    """Load and return JSON data from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_attack_configs():
    """Merge all attack configurations into one unified file."""
    
    # Base directory
    base_dir = Path(__file__).parent
    configs_dir = base_dir / "configs"
    
    # List of all attack config files
    attack_files = [
        configs_dir / "experiment_config.raw.json",  # Original WASP attacks
        configs_dir / "additional_attacks" / "adinject_attacks.json",
        configs_dir / "additional_attacks" / "redteamcua_attacks.json",
        configs_dir / "additional_attacks" / "browserart_attacks_fixed.json",
    ]
    
    # Initialize merged configuration
    merged_config = {
        "prompt_injections_setup_config": []
    }
    
    # Track attack names to avoid duplicates
    attack_names = set()
    
    # Merge all configurations
    for attack_file in attack_files:
        if attack_file.exists():
            print(f"Loading attacks from {attack_file}")
            config = load_json_file(attack_file)
            
            for attack in config.get("prompt_injections_setup_config", []):
                attack_name = attack.get("free_form_name", "unnamed_attack")
                
                # Skip duplicates but keep track
                if attack_name in attack_names:
                    print(f"  Skipping duplicate attack: {attack_name}")
                    continue
                
                attack_names.add(attack_name)
                
                # Add source information
                attack["source_project"] = attack_file.stem
                merged_config["prompt_injections_setup_config"].append(attack)
                print(f"  Added attack: {attack_name}")
        else:
            print(f"Warning: Attack file not found: {attack_file}")
    
    # Save merged configuration
    output_file = configs_dir / "experiment_config.merged_all.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_config, f, indent=2, ensure_ascii=False)
    
    print(f"\nMerged configuration saved to: {output_file}")
    print(f"Total attacks merged: {len(merged_config['prompt_injections_setup_config'])}")
    
    # Print summary by project
    print("\nAttack summary by project:")
    project_counts = {}
    for attack in merged_config["prompt_injections_setup_config"]:
        source = attack.get("source_project", "unknown")
        project_counts[source] = project_counts.get(source, 0) + 1
    
    for project, count in project_counts.items():
        print(f"  {project}: {count} attacks")

if __name__ == "__main__":
    merge_attack_configs()
