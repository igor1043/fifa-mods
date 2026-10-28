import copy
import json
from pathlib import Path
import unittest
from room_collision_r70 import solid_obstacles

DATA = Path(__file__).resolve().parents[3] / 'data/club_environment/room/runtime'

def real_obstacles():
    return (json.loads((DATA / 'room_roles_r62.json').read_text(encoding='utf8'))['obstacles']
            + json.loads((DATA / 'medical_room_r57.json').read_text(encoding='utf8'))['obstacles'])

class CollisionMetadataTests(unittest.TestCase):
    def test_only_two_merged_decorations_removed(self):
        original = real_obstacles()
        before = copy.deepcopy(original)
        result = solid_obstacles(original)
        self.assertEqual(original, before)
        self.assertEqual(len(original) - len(result), 2)
        removed = [b for b in original if b not in result]
        self.assertEqual({b['name'] for b in removed}, {'Sala do treinador / folhas'})
        self.assertEqual(result, [b for b in original if b not in removed])

    def test_large_walls_and_small_decorations_remain_solid(self):
        boxes = [dict(name='Sala / parede', lo=[-400,0,0], hi=[400,300,800]),
                 dict(name='Sala do treinador / folhas', lo=[0,0,0], hi=[20,30,40]),
                 dict(name='Maca', lo=[0,50,0], hi=[80,56,200])]
        self.assertEqual(solid_obstacles(boxes), boxes)

if __name__ == '__main__':
    unittest.main()
