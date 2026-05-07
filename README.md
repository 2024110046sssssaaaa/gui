# GUIHazard: Cross-Platform GUI Agent Security Benchmark

GUIHazard is a unified security benchmark framework for evaluating the safety risks of GUI Agents (Graphical User Interface Agents) across three platforms: **Desktop**, **Mobile**, and **Web**. The framework covers three major categories of security threats: User Misuse, Prompt Injection Attacks, and Model Misbehavior.

---

## Directory Structure

```
GUIHazard/
├── desktop/              # Desktop benchmark module (based on OS-Harm)
│   ├── assets/           # Test assets (emails, documents, images, etc.)
│   ├── crossplatform/    # Cross-platform attack test cases
│   │   ├── X08/         # Login confirmation inconsistency injection
│   │   ├── X09/         # Notification sync injection
│   │   ├── X10/         # SMS verification code leakage
│   │   ├── X11/         # Screen casting诱导攻击
│   │   └── X12/         # Clipboard poisoning
│   ├── desktop_env/     # Virtual machine environment management
│   ├── judge/           # LLM judgment module
│   ├── mm_agents/       # Multimodal Agent implementation
│   └── run.py           # Main entry script
│
├── mobile/              # Mobile benchmark module (based on MobileSafetyBench)
│   ├── attacks/         # Attack datasets
│   │   ├── 1_visual_perception_attacks/    # Visual perception attacks
│   │   ├── 2_environment_content_injection/# Environment content injection
│   │   ├── 3_direct_malicious_commands/   # Direct malicious commands
│   │   ├── 4_llm_reasoning_attacks/       # LLM reasoning attacks
│   │   └── 5_system_exploitation/          # System exploitation
│   ├── mobile_safety/   # Core framework
│   └── scripts/         # Run scripts
│
└── web/                 # Web benchmark module (based on WASP)
    ├── visualwebarena/  # WebArena environment implementation
    ├── webarena_prompt_injections/  # Prompt injection testing
    │   ├── configs/     # Attack configurations
    │   └── attacker_*.py # Attack executors
    └── configs/         # Configuration files
```

---

## Core Features

### 1. Desktop Benchmark (Desktop)

Based on [OS-Harm](https://arxiv.org/abs/2506.14866), testing GUI Agent security in desktop operating system environments.

**Supported Observation Types:**
- `screenshot`: Screenshot only
- `a11y_tree`: Accessibility tree description
- `screenshot_a11y_tree`: Screenshot + accessibility tree
- `som`: Set-of-Marks annotation

**Test Scenarios:**
| Category | Description | Task Count |
|----------|-------------|------------|
| Deliberate Misuse (test_misuse.json) | User actively requests harmful operations | ~50 |
| Prompt Injection (test_injection.json) | Malicious instructions embedded in web pages/documents | ~50 |
| Model Misbehavior (test_misbehavior.json) | Model's spontaneous unsafe behavior | ~50 |

**Usage Example:**
```bash
cd desktop
python run.py --path_to_vm Ubuntu/Ubuntu.vmx \
              --observation_type screenshot_a11y_tree \
              --model o4-mini \
              --result_dir ./results \
              --test_all_meta_path evaluation_examples/test_misuse.json
```

### 2. Mobile Benchmark (Mobile)

Based on [MobileSafetyBench](https://github.com/), testing mobile Agent security.

**Attack Types:**
| Category | Attack ID | Description |
|----------|-----------|-------------|
| Visual Perception Attack | M07 | Notification injection |
| Environment Content Injection | M08-M09 | Screen text injection, view tree interference |
| Direct Malicious Commands | M10-M12 | Prompt injection, privacy risk operations, harmful content generation |
| LLM Reasoning Attacks | M15-M16 | Malicious instruction exploitation, glitch token attacks |
| System Exploitation | M13, M20-M21 | Deep link forgery, notification overlay attacks, background attacks |

**Usage Example:**
```bash
cd mobile
python attacks/batch_runner.py --config attacks/config.yaml --model claude-3-5-sonnet
```

### 3. Web Benchmark (Web)

Based on [WASP](https://arxiv.org/abs/2504.18575), testing Web Agent resilience against prompt injection attacks.

**Supported Agents:**
- GPT-4o / GPT-4o-mini (WebArena framework)
- Claude-3.5 / Claude-3.7 (Computer Use framework)

**Supported Website Environments:**
- GitLab
- Reddit
- And more...

**Usage Example:**
```bash
cd web/webarena_prompt_injections
python run.py --config configs/experiment_config.raw.json \
              --model gpt-4o \
              --system-prompt configs/system_prompts/wa_p_som_cot_id_actree_3s.json \
              --output-dir ./results
```

### 4. Cross-Platform Attack Testing

The desktop module integrates **X08-X12** five categories of cross-platform attack tests, simulating scenarios where security channels between Desktop and Mobile are exploited:

| Test Set | Attack Type | Description |
|----------|-------------|-------------|
| **X08** | Login Confirmation Inconsistency | Desktop requests login, mobile verification info is tampered |
| **X09** | Notification Sync Injection | Desktop sync notifications injected with malicious content |
| **X10** | SMS Verification Code Leakage | Obtain and leak verification codes via sync channel |
| **X11** | Screen Casting Inducement | Injected misleading operations in screen casting content |
| **X12** | Clipboard Poisoning | Sync clipboard content injected with malicious markers |

**Running Cross-Platform Tests:**
```bash
cd desktop
python run_crossplatform_tests.py --test_set X08 --model o4-mini
```

**Metric Definitions (see `crossplatform/paper_evaluation_schema.json`):**
- `XP-ASR`: Cross-Platform Attack Success Rate
- `XP-DSR`: Cross-Platform Defense Success Rate
- `HSR`: Cross-End Information Transfer Success Rate
- `SCR/CCR/CFR/PR/RR`: Safe Completion/Compromised/Collaboration Failure/Partial/Refusal Rate

---

## Installation

### Common Dependencies
```bash
# Python 3.10+
pip install -r requirements.txt
```

### Desktop Additional Dependencies
```bash
# VMware Workstation (or supported VM providers)
# OSWorld environment (refer to OSWorld installation docs)
```

### Mobile Additional Dependencies
```bash
# Android SDK
# Appium
# Java 17
conda create -n mobile_safety python=3.10
pip install -r requirements.txt
```

### Web Additional Dependencies
```bash
# Docker
# Python 3.10
bash webarena_prompt_injections/setup.sh
```

---

## Evaluation Metrics

### General Metrics
| Metric | Description |
|--------|-------------|
| Attack Success Rate (ASR) | Proportion of successful attack executions |
| Defense Success Rate (DSR) | Proportion of successful defenses |
| Over-Defense Rate (ODR) | Proportion of normal tasks failed due to over-defense |

### Cross-Platform Metrics
| Metric | Description |
|--------|-------------|
| XP-ASR | Cross-Platform Attack Success Rate |
| HSR | Cross-End Information Transfer Success Rate |
| CCR | Compromised Completion Rate |
