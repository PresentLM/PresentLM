"""
Benchmark Visualization Script - Pipeline Performance Analysis
Creates a comprehensive visualization showing the sequential pipeline bottleneck
and the impact of progressive loading optimization.

Usage:
    python scripts/plot_benchmarks.py <benchmark_file.json>
    python scripts/plot_benchmarks.py  # Uses latest benchmark file
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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


def get_processing_events(events: List[Dict]) -> List[Dict]:
    """
    Extract processing pipeline events (SlideParser, NarrationGenerator, TTSEngine for narrations).
    Filters out Q&A events and Q&A-related TTS calls.
    
    Strategy:
    1. Find SlideParser and NarrationGenerator events
    2. Count number of slides from metadata
    3. Take the next N TTSEngine events (where N = num_slides)
    4. Stop before any STTEngine or QuestionHandler events
    """
    processing_events = []
    num_slides = None
    tts_count = 0
    
    # First pass: extract num_slides from metadata
    for event in events:
        if event['component'] == 'SlideParser' and 'metadata' in event:
            num_slides = event['metadata'].get('num_slides')
            break
        elif event['component'] == 'NarrationGenerator' and 'metadata' in event:
            num_slides = event['metadata'].get('num_slides')
            break
    
    # Second pass: extract processing events in order
    for event in events:
        component = event['component']
        
        # Stop if we hit Q&A components
        if component in ['STTEngine', 'QuestionHandler']:
            break
        
        # Add SlideParser and NarrationGenerator
        if component in ['SlideParser', 'NarrationGenerator']:
            processing_events.append(event)
        
        # Add TTSEngine only up to num_slides count
        elif component == 'TTSEngine':
            if num_slides is None or tts_count < num_slides:
                processing_events.append(event)
                tts_count += 1
    
    return processing_events


def aggregate_by_component(events: List[Dict]) -> Dict:
    """Aggregate events by component and operation."""
    component_times = defaultdict(list)
    
    for event in events:
        key = f"{event['component']}::{event['operation']}"
        component_times[key].append(event['duration_seconds'])
    
    return component_times


def create_pipeline_visualization(events: List[Dict], output_path: Optional[Path] = None) -> None:
    """
    Create a comprehensive visualization showing the sequential pipeline performance
    and the impact of progressive loading optimization.
    
    Shows:
    1. Sequential execution timeline with critical path highlighted
    2. Component latency breakdown with bottleneck identification
    3. Performance comparison table (before vs after optimization)
    """
    if not events:
        print("No events to visualize")
        return
    
    # Aggregate component times
    component_times = aggregate_by_component(events)
    
    # Define component order
    component_order = ['SlideParser', 'NarrationGenerator', 'TTSEngine']
    operation_labels = {
        'SlideParser::parse': 'Slide Parsing',
        'NarrationGenerator::generate_narration': 'Narration Generation',
        'TTSEngine::generate_audio': 'Text-to-Speech'
    }
    
    # Calculate timing data
    timeline_data = []
    current_time = 0
    total_time = 0
    
    for component in component_order:
        for key, times in component_times.items():
            if component in key:
                total_duration = sum(times)
                count = len(times)
                avg_duration = np.mean(times)
                
                timeline_data.append({
                    'component': component,
                    'label': operation_labels.get(key, key),
                    'start': current_time,
                    'duration': total_duration,
                    'avg_duration': avg_duration,
                    'count': count,
                    'key': key
                })
                
                current_time += total_duration
                total_time += total_duration
    
    # Create subplot figure
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '<b>(A) Sequential Pipeline Execution (Baseline)</b>',
            '<b>(B) Component Latency Distribution</b>',
            '<b>(C) Optimization Impact</b>'
        ),
        specs=[
            [{"type": "bar", "colspan": 2}, None],
            [{"type": "bar"}, {"type": "table"}]
        ],
        row_heights=[0.5, 0.5],
        vertical_spacing=0.2,
        horizontal_spacing=0.2
    )
    
    # Professional color scheme (lighter, more vibrant)
    colors = {
        'SlideParser': '#66BB6A',         # Light green - fast operation
        'NarrationGenerator': '#42A5F5',  # Light blue - moderate operation
        'TTSEngine': '#EF5350'            # Light red - bottleneck
    }
    
    # ============================================
    # Subplot 1: Sequential Timeline (Gantt-style)
    # ============================================
    for i, item in enumerate(timeline_data):
        # Use auto positioning for small bars
        text_position = 'auto' if item['duration'] < 1.0 else 'inside'
        
        fig.add_trace(go.Bar(
            name=item['label'],
            x=[item['duration']],
            y=['Pipeline<br>Execution'],
            orientation='h',
            marker=dict(
                color=colors[item['component']],
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=f"{item['label']}<br>{item['duration']:.2f}s",
            textposition=text_position,
            textfont=dict(size=14, color='white' if text_position == 'inside' else '#333', family='Arial'),
            base=item['start'],
            hovertemplate=(
                f"<b>{item['label']}</b><br>" +
                f"Duration: {item['duration']:.2f}s<br>" +
                f"Count: {item['count']}<br>" +
                "<extra></extra>"
            ),
            showlegend=False
        ), row=1, col=1)
    
    # Add critical path annotation
    fig.add_annotation(
        x=total_time / 2,
        y=0,
        text=f"<b>Total Blocking Time: {total_time:.1f}s</b><br><i>User cannot access presentation</i>",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor='#D32F2F',
        ax=0,
        ay=-70,
        font=dict(size=15, color='#333', family='Arial'),
        bgcolor='rgba(255,235,235,0.95)',
        bordercolor='#D32F2F',
        borderwidth=2,
        borderpad=6,
        row=1, col=1
    )
    
    # ============================================
    # Subplot 2: Component Breakdown
    # ============================================
    component_names = [item['label'] for item in timeline_data]
    durations = [item['duration'] for item in timeline_data]
    percentages = [d / total_time * 100 for d in durations]
    bar_colors = [colors[item['component']] for item in timeline_data]
    
    fig.add_trace(go.Bar(
        x=component_names,
        y=durations,
        marker=dict(
            color=bar_colors,
            line=dict(color='rgba(0,0,0,0.3)', width=1)
        ),
        text=[f"{d:.2f}s<br>({p:.1f}%)" for d, p in zip(durations, percentages)],
        textposition='outside',
        textfont=dict(size=15, family='Arial'),
        hovertemplate=(
            "<b>%{x}</b><br>" +
            "Time: %{y:.2f}s<br>" +
            "<extra></extra>"
        ),
        showlegend=False
    ), row=2, col=1)
    
    # Highlight TTS as bottleneck
    tts_idx = next((i for i, item in enumerate(timeline_data) if item['component'] == 'TTSEngine'), None)
    if tts_idx is not None:
        fig.add_annotation(
            x=tts_idx,
            y=durations[tts_idx] * 0.35,  # Position lower in the bar to avoid text overlap
            text="Primary Bottleneck",
            showarrow=False,
            font=dict(size=13, color='#333', family='Arial'),
            bgcolor='rgba(255,235,235,0.95)',
            bordercolor='#D32F2F',
            borderwidth=2,
            borderpad=4,
            row=2, col=1
        )
    
    # ============================================
    # Subplot 3: Optimization Impact Table
    # ============================================
    # Calculate first slide time vs total time
    # With progressive loading: parse all slides + first narration + first audio
    first_slide_time = (
        timeline_data[0]['duration'] +           # SlideParser (all slides)
        timeline_data[1]['avg_duration'] +       # NarrationGenerator (1 slide)
        timeline_data[2]['avg_duration']         # TTSEngine (1 slide audio)
    )
    time_saved = total_time - first_slide_time
    improvement_pct = (time_saved / total_time) * 100
    
    table_data = [
        ['Metric', 'Sequential', 'Progressive', 'Improvement'],
        ['Time to First Slide', f'{total_time:.2f}s', f'{first_slide_time:.2f}s', f'{improvement_pct:.1f}% faster'],
        ['User Experience', 'Blocking', 'Non-blocking', 'Progressive loading'],
        ['Audio Generation', 'Synchronous', 'Asynchronous', 'Background processing']
    ]
    
    # Extract columns
    headers = table_data[0]
    cells = list(zip(*table_data[1:]))
    
    fig.add_trace(go.Table(
        header=dict(
            values=headers,
            fill_color='#1565C0',
            align='left',
            font=dict(color='white', size=16, family='Arial'),
            height=35
        ),
        cells=dict(
            values=cells,
            fill_color=[['#f5f5f5', 'white', '#f5f5f5', 'white']],
            align='left',
            font=dict(color='#333', size=15, family='Arial'),
            height=32
        )
    ), row=2, col=2)
    
    # ============================================
    # Layout Configuration
    # ============================================
    fig.update_xaxes(title_text="Time (seconds)", row=1, col=1, showgrid=True, gridcolor='#E0E0E0')
    fig.update_xaxes(title_text="Component", row=2, col=1, showgrid=False)
    fig.update_yaxes(showticklabels=False, row=1, col=1)
    # Set y-axis range for component breakdown to accommodate labels above bars
    max_duration = max(durations) if durations else 0
    fig.update_yaxes(
        title_text="Time (seconds)", 
        row=2, col=1, 
        showgrid=True, 
        gridcolor='#E0E0E0',
        range=[0, max_duration * 1.2]  # Add 20% padding for text labels
    )
    
    fig.update_layout(
        height=1000,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='#FAFAFA',
        font=dict(family='Arial', size=15, color='#333'),
        margin=dict(t=80, b=60, l=60, r=60)
    )
    
    # Update subplot title font size
    for i, annotation in enumerate(fig['layout']['annotations']):
        # Only update the first 4 annotations which are subplot titles
        # (not the custom annotations like "Total Blocking Time" and "Primary Bottleneck")
        if i < 4 and annotation['text'] and annotation['text'].startswith('<b>'):
            annotation['font'] = dict(size=14, family='Arial')
    
    # Save or show
    if output_path:
        fig.write_html(output_path.with_suffix('.html'))
        print(f"✓ Saved interactive: {output_path.with_suffix('.html')}")
        
        # Also save as static image if kaleido is available
        try:
            fig.write_image(output_path, width=1600, height=900, scale=2)
            print(f"✓ Saved static: {output_path}")
        except Exception as e:
            print(f"⚠ Could not save static image: {e}")
    else:
        fig.show()


def print_pipeline_stats(events: List[Dict]) -> None:
    """Print statistics for the pipeline."""
    if not events:
        print("\nNo events recorded")
        return
    
    component_times = aggregate_by_component(events)
    
    print(f"\n{'='*80}")
    print(f"PROCESSING PIPELINE ANALYSIS")
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
    print(f"Total Operations: {total_ops}")
    print(f"Total Pipeline Time: {total_time:.3f}s")
    print(f"Average Per Operation: {total_time/total_ops:.3f}s")
    print(f"{'='*80}\n")


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
    
    # Extract processing pipeline events only
    processing_events = get_processing_events(data['events'])
    
    # Print statistics
    print_pipeline_stats(processing_events)
    
    # Create output directory
    output_dir = benchmark_file.parent / "graphs"
    output_dir.mkdir(exist_ok=True)
    
    # Generate the pipeline performance visualization
    print("\nGenerating pipeline performance visualization...")
    
    output_path = output_dir / "pipeline_analysis.png"
    create_pipeline_visualization(processing_events, output_path)
    
    print(f"\n✓ Visualization saved to: {output_dir}\n")
    print("Interactive HTML version available:")
    print(f"   {output_dir / 'pipeline_analysis.html'}\n")


if __name__ == "__main__":
    main()
