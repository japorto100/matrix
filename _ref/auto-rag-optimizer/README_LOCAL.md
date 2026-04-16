# Local Experiment Runner

Run Auto-RAG-Optimizer experiments locally without GitHub Actions.

## Setup

1. Set your OpenRouter API key:
```bash
export OPENROUTER_API_KEY="your-key-here"
# or create .env file:
echo "OPENROUTER_API_KEY=your-key-here" > .env
```

2. Install dependencies (if not already):
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Single Experiment
```bash
python run_experiments.py --single
```

### Automatic Experiments
```bash
# Run 10 experiments (60s interval between runs)
python run_experiments.py --auto 10

# Run 5 experiments with 30s interval
python run_experiments.py --auto 5 --interval 30
```

### Interactive Mode
```bash
python run_experiments.py --interactive
```

Interactive commands:
- `run` - Run single experiment
- `auto N` - Run N experiments
- `status` - Show current config
- `quit` - Exit

### Custom Config
```bash
python run_experiments.py --single --config my_config.json
```

## Features

- **No GitHub Actions needed** - runs completely locally
- **Manual control** - run experiments when you want
- **Automatic mode** - continuous optimization
- **Interactive mode** - command-by-command control
- **Cost tracking** - see token usage and costs in real-time
- **Charts generation** - automatic visualization after experiments

## Output

- `research_log.md` - Experiment results table
- `charts/` - Visualizations (generated automatically)
- `best_config.json` - Best performing configuration
- `scores.json` - Latest evaluation scores

## Stopping Experiments

- Press `Ctrl+C` to stop automatic runs
- Type `quit` in interactive mode
- Experiments save progress automatically
