#!/usr/bin/env python3
"""
Local experiment runner for Auto-RAG-Optimizer
Supports both automatic and manual experiment modes
"""

import argparse
import logging
import sys
import time
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from orchestrator import orchestrate, load_config
from rag_pipeline import CONFIG_PATH

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_single_experiment(config_file=None):
    """Run a single experiment with current or specified config"""
    if config_file and config_file != CONFIG_PATH:
        # Load specified config and save as current
        import json
        config = load_config(config_file)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Loaded config from {config_file}")
    
    logger.info("Running single experiment...")
    orchestrate(max_runs=1, interval=0)
    logger.info("Single experiment complete!")


def run_automatic_experiments(max_runs=20, interval=60):
    """Run automatic experiments continuously"""
    logger.info(f"Starting automatic experiments: max_runs={max_runs}, interval={interval}s")
    
    try:
        orchestrate(max_runs=max_runs, interval=interval)
    except KeyboardInterrupt:
        logger.info("Automatic experiments stopped by user")
    except Exception as e:
        logger.error(f"Automatic experiments failed: {e}")
        sys.exit(1)


def run_interactive_mode():
    """Interactive mode for manual experiment control"""
    print("\n=== Auto-RAG-Optimizer Interactive Mode ===")
    print("Commands:")
    print("  run     - Run single experiment")
    print("  auto N  - Run N experiments automatically")
    print("  status  - Show current config")
    print("  quit    - Exit")
    print()
    
    while True:
        try:
            cmd = input(">>> ").strip().lower()
            
            if cmd == "quit" or cmd == "q":
                print("Goodbye!")
                break
            elif cmd == "run" or cmd == "r":
                run_single_experiment()
            elif cmd.startswith("auto "):
                try:
                    n = int(cmd.split()[1])
                    run_automatic_experiments(max_runs=n, interval=5)
                except (ValueError, IndexError):
                    print("Usage: auto N (where N is number of experiments)")
            elif cmd == "status" or cmd == "s":
                config = load_config()
                print(f"\nCurrent config:")
                for key, value in config.items():
                    print(f"  {key}: {value}")
                print()
            elif cmd == "help" or cmd == "h":
                print("Commands: run, auto N, status, quit")
            else:
                print("Unknown command. Type 'help' for commands.")
                
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            break


def main():
    parser = argparse.ArgumentParser(
        description="Run Auto-RAG-Optimizer experiments locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single experiment
  python run_experiments.py --single
  
  # Run 10 experiments automatically (60s interval)
  python run_experiments.py --auto 10
  
  # Run 5 experiments with 30s interval
  python run_experiments.py --auto 5 --interval 30
  
  # Interactive mode
  python run_experiments.py --interactive
  
  # Use custom config
  python run_experiments.py --single --config my_config.json
        """
    )
    
    parser.add_argument("--single", action="store_true", 
                       help="Run single experiment")
    parser.add_argument("--auto", type=int, metavar="N",
                       help="Run N experiments automatically")
    parser.add_argument("--interval", type=int, default=60, metavar="SECONDS",
                       help="Interval between automatic runs (default: 60)")
    parser.add_argument("--interactive", action="store_true",
                       help="Interactive mode with command prompt")
    parser.add_argument("--config", type=str, metavar="FILE",
                       help="Use specific config file (for single run)")
    
    args = parser.parse_args()
    
    # Check environment
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not found! Set it in .env file or environment.")
        sys.exit(1)
    
    if args.interactive:
        run_interactive_mode()
    elif args.single:
        run_single_experiment(args.config)
    elif args.auto:
        run_automatic_experiments(max_runs=args.auto, interval=args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
