#!/usr/bin/env python3
"""
Script to validate the merged attack configuration file.
"""

import json
import sys
from pathlib import Path

def validate_attack_config(config_path):
    """Validate the attack configuration file."""
    print(f"Validating {config_path}...")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    attacks = config.get("prompt_injections_setup_config", [])
    print(f"Total attacks: {len(attacks)}")
    
    # Required fields for each attack
    required_fields = [
        "free_form_name",
        "environment", 
        "action_url",
        "instruction",
        "eval",
        "cleanup_fn"
    ]
    
    # Validate each attack
    errors = []
    warnings = []
    
    for i, attack in enumerate(attacks):
        name = attack.get("free_form_name", f"Attack #{i}")
        
        # Check required fields
        for field in required_fields:
            if field not in attack:
                errors.append(f"{name}: Missing required field '{field}'")
        
        # Check eval structure
        eval_config = attack.get("eval", {})
        if "eval_types" not in eval_config:
            warnings.append(f"{name}: No eval_types specified")
        
        # Check environment
        env = attack.get("environment")
        if env not in ["gitlab", "reddit"]:
            warnings.append(f"{name}: Unknown environment '{env}'")
        
        # Check parameters
        params = attack.get("parameters", {})
        if env == "gitlab" and "project_owner" not in params:
            warnings.append(f"{name}: GitLab attack missing project_owner")
        if env == "reddit" and "attacker_username" not in params:
            warnings.append(f"{name}: Reddit attack missing attacker_username")
    
    # Print results
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("\n⚠️ WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("\n✅ All attacks validated successfully!")
    elif not errors:
        print("\n✅ All attacks validated with warnings")
    else:
        print(f"\n❌ Validation failed with {len(errors)} errors")
        return False
    
    # Print attack summary by environment
    print("\n📊 Attack Summary by Environment:")
    env_counts = {}
    for attack in attacks:
        env = attack.get("environment", "unknown")
        env_counts[env] = env_counts.get(env, 0) + 1
    
    for env, count in env_counts.items():
        print(f"  {env}: {count} attacks")
    
    # Print attack summary by source
    print("\n📊 Attack Summary by Source:")
    source_counts = {}
    for attack in attacks:
        source = attack.get("source_project", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    
    for source, count in source_counts.items():
        print(f"  {source}: {count} attacks")
    
    return len(errors) == 0

if __name__ == "__main__":
    config_path = Path(__file__).parent / "configs" / "experiment_config.merged_all.json"
    
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    success = validate_attack_config(config_path)
    sys.exit(0 if success else 1)
