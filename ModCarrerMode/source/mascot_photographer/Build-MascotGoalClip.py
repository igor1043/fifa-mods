"""Bake a coherent, read-only FIFA crowd goal capture; keep waypoint applause separate."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation, Slerp


def number(value):
    value = 0.0 if abs(value) < 1e-9 else value
    text = f'{value:.8g}'
    if '.' not in text and 'e' not in text:
        text += '.0'
    return text + 'f'


def bake(source, output, header, prefix='mascotGoal'):
    capture = json.loads(source.read_text(encoding='utf8'))
    frames = capture['frames']
    times = np.array([f['time'] for f in frames])
    times -= times[0]
    if len(times) < 60 or np.any(np.diff(times) <= 0) or np.max(np.diff(times)) > .20:
        raise ValueError('Capture must be a continuous, ordered playing segment')
    if any(f['behavior'] != 14 or f['clip'] != capture['clip'] or
           f['slot'] != capture['slot'] for f in frames):
        raise ValueError('Mixed crowd behavior, clip or actor')
    matrices = np.array([f['matrices'] for f in frames]).reshape(-1, 31, 4, 4).transpose(0, 1, 3, 2)
    if not np.all(np.isfinite(matrices)):
        raise ValueError('Nonfinite pose')
    positions = matrices[:, :, :3, 3].copy()
    quats = np.stack([Rotation.from_matrix(m[:, :3, :3]).as_quat() for m in matrices])
    feet = np.minimum(positions[:, 5, 1], positions[:, 9, 1])
    # Preserve captured airborne motion independently of the mascot foot-ground
    # correction. Human reference bone translations are in centimetres.
    lift = np.maximum(0, feet - np.percentile(feet, 10) - 3) if capture.get('jump') else np.zeros(len(times))
    # Smooth the loop endpoint; this never changes or replaces the native gesture.
    duration = float(times[-1])
    for i, t in enumerate(times):
        alpha = np.clip((t - (duration - .35)) / .35, 0, 1)
        alpha = alpha * alpha * (3 - 2 * alpha)
        if alpha > 0:
            lift[i] = lift[i] * (1 - alpha) + lift[0] * alpha
            positions[i] = positions[i] * (1 - alpha) + positions[0] * alpha
            for bone in range(31):
                quats[i, bone] = Slerp([0, 1], Rotation.from_quat([quats[i, bone], quats[0, bone]]))([alpha]).as_quat()[0]
    poses = np.concatenate([positions, quats], axis=2).reshape(-1, 217)
    baked = []
    for i, t in enumerate(times):
        m = np.tile(np.eye(4), (31, 1, 1))
        m[:, :3, :3] = Rotation.from_quat(quats[i]).as_matrix()
        m[:, :3, 3] = positions[i]
        baked.append({'time': float(t), 'matrices': m.transpose(0, 2, 1).reshape(-1).round(7).tolist()})
    provenance = {key: capture[key] for key in ('behavior', 'clip', 'slot', 'source')}
    output.write_text(json.dumps({'duration': duration, 'provenance': provenance, 'liftCm': lift.round(7).tolist(), 'frames': baked}), encoding='utf8')
    text = '#pragma once\n// Native FIFA CrowdAI home-goal reaction, captured read-only. Waypoint applause is independent.\n'
    text += f'static constexpr int mascotGoalSourceBehavior={capture["behavior"]};\n'
    text += f'static constexpr int mascotGoalSourceClip={capture["clip"]};\n'
    text += f'static constexpr float mascotGoalDuration={number(duration)};\n'
    text += f'static constexpr unsigned int mascotGoalFrameCount={len(times)};\n'
    text += 'static constexpr float mascotGoalTimes[]={' + ','.join(map(number, times)) + '};\n'
    text += 'static const float mascotGoalLift[]={' + ','.join(map(number, lift)) + '};\n'
    text += 'static const float mascotGoalFrames[' + str(len(times)) + '][31*7]={\n'
    text += ',\n'.join(' {' + ','.join(map(number, pose)) + '}' for pose in poses) + '\n};\n'
    header.write_text(text.replace('mascotGoal', prefix), encoding='utf8')
    print(json.dumps({'duration': duration, 'frames': len(times), 'source': provenance}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--header', type=Path, required=True)
    parser.add_argument('--prefix', default='mascotGoal')
    args = parser.parse_args()
    bake(args.capture, args.output, args.header, args.prefix)
