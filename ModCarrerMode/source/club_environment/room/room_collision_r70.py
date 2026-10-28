"""Indoor collision metadata corrections; never changes visible geometry."""

def solid_obstacles(obstacles):
    """Discard only the two legacy bounds spanning separate decorative leaves.

    Those batches span nearly eight metres, including the coach room entrance.
    Their enclosing AABB is empty walking space, not a solid wall or furniture.
    All actual wall, doorway, table, chair and medical colliders are retained.
    """
    return [box for box in obstacles if not (
        box.get('name') == 'Sala do treinador / folhas'
        and box['hi'][0] - box['lo'][0] > 600
        and box['hi'][2] - box['lo'][2] > 600)]
