"""Executed XY coverage; length alone can reward repeated loops."""
import argparse
import json
import math
from pathlib import Path


def measure(states, cell_size=0.5):
    if not math.isfinite(cell_size) or cell_size <= 0:
        raise ValueError('cell_size must be finite and positive')
    if not states:
        raise ValueError('trajectory is empty')
    points = [(float(s['position'][0]), float(s['position'][1])) for s in states]
    times = [float(s['time_s']) for s in states]
    if not all(math.isfinite(v) for p in points for v in p) or not all(math.isfinite(t) for t in times):
        raise ValueError('nonfinite trajectory')
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('timestamps must increase')
    cells = {(math.floor(x / cell_size), math.floor(y / cell_size)) for x, y in points}
    length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    xs, ys = zip(*points)
    return {
        'duration_s': times[-1] - times[0],
        'sample_count': len(points),
        'executed_xy_length_m': length,
        'start_to_finish_m': math.dist(points[0], points[-1]),
        'maximum_distance_from_start_m': max(math.dist(points[0], p) for p in points),
        'xy_extent_m': [max(xs) - min(xs), max(ys) - min(ys)],
        'visited_grid_cells': len(cells),
        'grid_cell_size_m': cell_size,
        'grid_origin_world_xy_m': [0, 0],
        'scope': 'Observed root XY samples; no interpolation, free-space coverage or safety certification.',
        'length_caveat': 'Root sway and repeated travel contribute to length; compare extent and unique cells too.',
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('report')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = measure(json.loads(Path(a.report).read_text())['states'])
    Path(a.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
