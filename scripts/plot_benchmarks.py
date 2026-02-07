"""
Benchmark Visualization Script - Dual Pipeline
Separates and plots Upload and Q&A pipelines.

Usage:
    python scripts/plot_benchmarks.py <benchmark_file.json>
    python scripts/plot_benchmarks.py  # Uses latest benchmark file
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import Config


def load_benchmark_data(filepath: Path) -> Dict:
    """Load benchmark data from JSON file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Benchmark file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        return json.load(f)


def find_latest_benchmark() -> Path:
    """Find the most recent benchmark file."""
    benchmark_files = list(Config.DATA_DIR.glob("benchmark_*.json"))
    
    if not benchmark_files:
        raise FileNotFoundError("No benchmark files found in data directory")
    
    latest = max(benchmark_files, key=lambda p: p.stat().st_mtime)
    return latest


def classify_events(events: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Classify events into processing and Q&A pipelines.
    
    Processing pipeline: SlideParser, NarrationGenerator, TTSEngine (for narrations)
    Q&A pipeline: STTEngine, QuestionHandler, TTSEngine (for answers)
    """
    upload_events = []
    qa_events = []
    
    # Check if we have STT or QuestionHandler events (indicators of Q&A)
    has_qa = any(e['component'] in ['STTEngine', 'QuestionHandler'] for e in events)
    
    if not has_qa:
        # No Q&A, all events are processing pipeline
        return events, []
    
    # Separate events: processing comes first with SlideParser/NarrationGenerator
    # Q&A comes after with STTEngine/QuestionHandler
    for event in events:
        if event['component'] in ['STTEngine', 'QuestionHandler']:
            qa_events.append(event)
        elif event['component'] == 'TTSEngine':
            # TTSEngine used in both - figure out which based on position
            # If there are STT/QuestionHandler events, assume TTSEngine after index check
            if len(upload_events) > 0 and upload_events[-1]['component'] == 'NarrationGenerator':
                # This TTSEngine follows NarrationGenerator -> processing pipeline
                upload_events.append(event)
            elif len(qa_events) > 0 and any(e['component'] in ['STTEngine', 'QuestionHandler'] for e in qa_events):
                # We have Q&A events, so this TTSEngine is likely for Q&A
                qa_events.append(event)
            else:
                # Default to processing if unclear
                upload_events.append(event)
        else:
            # SlideParser, NarrationGenerator -> processing pipeline
            upload_events.append(event)
    
    return upload_events, qa_events


def aggregate_by_component(events: List[Dict]) -> Dict:
    """Aggregate events by component and operation."""
    component_times = defaultdict(list)
    
    for event in events:
        key = f"{event['component']}::{event['operation']}"
        component_times[key].append(event['duration_seconds'])
    
    return component_times


def plot_pipeline_latencies(name: str, events: List[Dict], output_path: Optional[Path] = None) -> None:
    """Plot latencies for a specific pipeline."""
    if not events:
        return
    
    component_times = aggregate_by_component(events)
    
    # Create ordered list of operations
    operation_order = {
        'SlideParser::parse': 0,
        'NarrationGenerator::generate_narration': 1,
        'STTEngine::transcribe': 0,
        'QuestionHandler::answer_question': 1,
        'TTSEngine::generate_audio': 2,
    }
    
    # Sort by operation order
    sorted_ops = sorted(
        component_times.items(),
        key=lambda x: operation_order.get(x[0], 999)
    )
    
    op_names = [op.split('::')[1] for op, _ in sorted_ops]
    timings = [
        (np.mean(times), np.min(times), np.max(times))
        for _, times in sorted_ops
    ]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7B731', '#5F27CD']
    x = np.arange(len(op_names))
    
    avgs = [t[0] for t in timings]
    mins = [t[1] for t in timings]
    maxs = [t[2] for t in timings]
    
    errors = [np.array(avgs) - np.array(mins), np.array(maxs) - np.array(avgs)]
    
    bars = ax.bar(x, avgs, yerr=errors, capsize=10, color=colors[:len(op_names)],
                  edgecolor='black', linewidth=2, alpha=0.8,
                  error_kw={'elinewidth': 2, 'capthick': 3})
    
    # Add value labels
    for i, (bar, avg, min_v, max_v) in enumerate(zip(bars, avgs, mins, maxs)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{avg:.2f}s\n({min_v:.2f}s-{max_v:.2f}s)',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Calculate total pipeline time
    total_time = sum(avgs)
    
    ax.set_ylabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_title(f'{name} Pipeline Latencies\nTotal: {total_time:.2f}s', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(op_names, fontsize=11, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    else:
        plt.show()


def plot_pipeline_timeline(name: str, events: List[Dict], output_path: Optional[Path] = None) -> None:
    """Plot timeline of sequential execution for a pipeline."""
    if not events:
        return
    
    component_times = aggregate_by_component(events)
    
    # Order operations sequentially
    operation_order = {
        'SlideParser::parse': 0,
        'NarrationGenerator::generate_narration': 1,
        'STTEngine::transcribe': 0,
        'QuestionHandler::answer_question': 1,
        'TTSEngine::generate_audio': 2,
    }
    
    sorted_ops = sorted(
        component_times.items(),
        key=lambda x: operation_order.get(x[0], 999)
    )
    
    fig, ax = plt.subplots(figsize=(14, 5))
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    y_pos = 1
    current_time = 0
    
    for idx, (op_key, times) in enumerate(sorted_ops):
        avg_time = np.mean(times)
        op_name = op_key.split('::')[1]
        color = colors[min(idx, len(colors)-1)]
        
        # Draw bar
        ax.barh(y_pos, avg_time, left=current_time, height=0.4,
                color=color, edgecolor='black', linewidth=2)
        
        # Add label above the bar
        mid_point = current_time + avg_time / 2
        ax.text(mid_point, y_pos + 0.35, f'{op_name}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # Add time value above the label
        ax.text(mid_point, y_pos + 0.55, f'{avg_time:.2f}s',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color='#333')
        
        current_time += avg_time
    
    # Add total at the end
    ax.text(current_time + 0.3, y_pos, f'Total: {current_time:.2f}s',
            fontsize=12, fontweight='bold', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    ax.set_ylim(0.3, 1.8)
    ax.set_xlim(0, current_time + 2)
    ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_title(f'{name} Pipeline Timeline', fontsize=14, fontweight='bold', pad=20)
    ax.set_yticks([])
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    else:
        plt.show()


def plot_total_time_by_component(events: List[Dict], output_path: Optional[Path] = None) -> None:
    """Plot total time spent in each component across all events."""
    if not events:
        return
    
    component_total_time = defaultdict(float)
    component_count = defaultdict(int)
    
    for event in events:
        component = event['component']
        component_total_time[component] += event['duration_seconds']
        component_count[component] += 1
    
    # Sort by total time
    components = sorted(component_total_time.items(), key=lambda x: x[1], reverse=True)
    comp_names = [c[0] for c in components]
    comp_times = [c[1] for c in components]
    comp_counts = [component_count[c] for c in comp_names]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7B731', '#5F27CD']
    x = np.arange(len(comp_names))
    bars = ax.bar(x, comp_times, color=colors[:len(comp_names)], edgecolor='black', linewidth=2, alpha=0.8)
    
    # Add value labels
    for bar, time, count in zip(bars, comp_times, comp_counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{time:.2f}s\n({count}x)',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.set_ylabel('Total Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('Total Latency by Component (All Events)', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(comp_names, fontsize=11, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    else:
        plt.show()


def plot_time_distribution(events: List[Dict], output_path: Optional[Path] = None) -> None:
    """Plot time distribution as a pie chart with legend."""
    if not events:
        return
    
    component_total_time = defaultdict(float)
    
    for event in events:
        component = event['component']
        component_total_time[component] += event['duration_seconds']
    
    # Sort by total time
    components = sorted(component_total_time.items(), key=lambda x: x[1], reverse=True)
    comp_names = [c[0] for c in components]
    comp_times = [c[1] for c in components]
    
    # Calculate percentages
    total_time = sum(comp_times)
    percentages = [t / total_time * 100 for t in comp_times]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = plt.cm.Set3(np.linspace(0, 1, len(comp_names)))
    
    # Create pie chart without labels (cleaner look)
    wedges, autotexts = ax.pie(comp_times, colors=colors, startangle=90,
                                textprops={'fontsize': 0})  # Hide text on pie
    
    # Create legend with component names and percentages
    legend_labels = [f'{name}: {time:.2f}s ({pct:.1f}%)' 
                     for name, time, pct in zip(comp_names, comp_times, percentages)]
    ax.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0.5),
              fontsize=11, frameon=True)
    
    ax.set_title('Time Distribution Across Components (All Events)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    else:
        plt.show()


def print_pipeline_stats(name: str, events: List[Dict]) -> None:
    """Print statistics for a pipeline."""
    if not events:
        print(f"\n{name}: No events recorded")
        return
    
    component_times = aggregate_by_component(events)
    
    print(f"\n{'='*80}")
    print(f"{name.upper()}")
    print(f"{'='*80}")
    
    total_time = sum(e['duration_seconds'] for e in events)
    total_ops = len(events)
    
    for key in sorted(component_times.keys()):
        times = component_times[key]
        print(f"\n{key}")
        print(f"  Count:     {len(times)}")
        print(f"  Avg:       {np.mean(times):.3f}s")
        print(f"  Min/Max:   {np.min(times):.3f}s / {np.max(times):.3f}s")
        print(f"  Total:     {sum(times):.3f}s")
    
    print(f"\n{'-'*80}")
    print(f"Operations: {total_ops} | Total Time: {total_time:.3f}s")
    print(f"{'='*80}")


def main():
    """Main entry point."""
    
    # Determine benchmark file
    if len(sys.argv) > 1:
        benchmark_file = Path(sys.argv[1])
    else:
        print("Finding latest benchmark file...")
        benchmark_file = find_latest_benchmark()
    
    print(f"\nLoading: {benchmark_file.name}\n")
    data = load_benchmark_data(benchmark_file)
    
    # Classify events into pipelines
    upload_events, qa_events = classify_events(data['events'])
    all_events = data['events']
    
    # Print statistics
    print_pipeline_stats("Processing Pipeline", upload_events)
    print_pipeline_stats("Q&A Pipeline", qa_events)
    
    # Create output directory
    output_dir = benchmark_file.parent / "graphs"
    output_dir.mkdir(exist_ok=True)
    
    # Generate separate graphs for each pipeline
    print("\nGenerating graphs...")
    
    if upload_events:
        upload_timeline = output_dir / "01_processing_pipeline_timeline.png"
        plot_pipeline_timeline("Processing", upload_events, upload_timeline)
        
        upload_latencies = output_dir / "02_processing_pipeline_latencies.png"
        plot_pipeline_latencies("Processing", upload_events, upload_latencies)
    
    if qa_events:
        qa_timeline = output_dir / "03_qa_pipeline_timeline.png"
        plot_pipeline_timeline("Q&A", qa_events, qa_timeline)
        
        qa_latencies = output_dir / "04_qa_pipeline_latencies.png"
        plot_pipeline_latencies("Q&A", qa_events, qa_latencies)
    
    # Generate overall component statistics
    total_time_path = output_dir / "05_total_time_by_component.png"
    plot_total_time_by_component(all_events, total_time_path)
    
    distribution_path = output_dir / "06_time_distribution.png"
    plot_time_distribution(all_events, distribution_path)
    
    print(f"\n✓ Graphs saved to: {output_dir}\n")


if __name__ == "__main__":
    main()
